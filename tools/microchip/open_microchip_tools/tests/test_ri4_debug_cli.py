import json
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mchp_ri4.icd4_comms_usb import ICD4CommsUsb
from mchp_ri4.ri4_debug_cli import TracingTransport, main
from mchp_ri4.transport import FakeTransport


def _u32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


class TestRi4DebugCli(unittest.TestCase):
    def test_tracing_transport_records_headers(self):
        transport = FakeTransport()
        transport.queue_recv(0x81, b"\x0d\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00")
        traced = TracingTransport(transport)

        traced.send(0x02, b"\x00\x01\x00\x40\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00", 1000)
        traced.recv(0x81, 1024, 1000)

        self.assertEqual(len(traced.trace), 2)
        self.assertEqual(traced.trace[0].header["messageType"], "0x40000100")
        self.assertEqual(traced.trace[1].endpoint, "0x81")

    def test_progress_command_returns_trace_json(self):
        side_out = 0x02
        side_in = 0x81

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == side_out and data == bytes((ICD4CommsUsb.COMMAND_PROGRESS,)):
                transport.queue_recv(side_in, b"\xAA\xBB")

        transport = FakeTransport(on_send=on_send)

        with patch("mchp_ri4.ri4_debug_cli._discover_pid", return_value=0x9012), patch(
            "mchp_ri4.ri4_debug_cli.PyusbTransport", return_value=transport
        ), patch("builtins.print") as mock_print:
            exit_code = main(["--tool", "pk4", "progress"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(mock_print.call_args[0][0])
        self.assertEqual(payload["responseHex"], "aabb")
        self.assertEqual(payload["trace"][0]["endpoint"], "0x02")
        self.assertEqual(payload["trace"][1]["endpoint"], "0x81")

    def test_named_script_failure_returns_trace_json(self):
        side_out = 0x02

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == side_out:
                raise RuntimeError("boom")

        transport = FakeTransport(on_send=on_send)

        with patch("mchp_ri4.ri4_debug_cli._discover_pid", return_value=0x9012), patch(
            "mchp_ri4.ri4_debug_cli.PyusbTransport", return_value=transport
        ), patch(
            "mchp_ri4.ri4_debug_cli.resolve_repo_scripts_path", return_value=r"c:\\repo\\scripts.yaml.gz"
        ), patch(
            "mchp_ri4.ri4_debug_cli.DeviceFile.from_xml_path"
        ) as mock_device_file, patch("builtins.print") as mock_print:
            mock_device_file.return_value.getScriptBasic.return_value = SimpleNamespace(
                method="EnterProgrammingMode", getData=lambda: b"\x39\x01"
            )
            exit_code = main(
                [
                    "--tool",
                    "pk4",
                    "named-script",
                    "--processor",
                    "dsPIC30F5011",
                    "--family",
                    "DSPIC30F",
                    "--script-name",
                    "EnterProgrammingMode",
                ]
            )

        self.assertEqual(exit_code, 1)
        payload = json.loads(mock_print.call_args[0][0])
        self.assertEqual(payload["errorType"], "RuntimeError")
        self.assertEqual(payload["trace"][0]["endpoint"], "0x02")

    def test_script_sequence_runs_multiple_steps(self):
        side_out = 0x02
        side_in = 0x81

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == side_out:
                transport.queue_recv(
                    side_in,
                    b"\x0d\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00",
                )

        transport = FakeTransport(on_send=on_send)

        with patch("mchp_ri4.ri4_debug_cli._discover_pid", return_value=0x9012), patch(
            "mchp_ri4.ri4_debug_cli.PyusbTransport", return_value=transport
        ), patch(
            "mchp_ri4.ri4_debug_cli.resolve_repo_scripts_path", return_value=r"c:\\repo\\scripts.yaml.gz"
        ), patch(
            "mchp_ri4.ri4_debug_cli.DeviceFile.from_xml_path"
        ) as mock_device_file, patch("builtins.print") as mock_print:
            def get_script(name: str):
                return SimpleNamespace(method=name, getData=lambda: b"\x39\x01")

            mock_device_file.return_value.getScriptBasic.side_effect = get_script
            exit_code = main(
                [
                    "--tool",
                    "pk4",
                    "--timeout-ms",
                    "1000",
                    "script-sequence",
                    "--processor",
                    "dsPIC30F5011",
                    "--family",
                    "DSPIC30F",
                    "--script-name",
                    "EnterTMOD_HV",
                    "--script-name",
                    "GetDeviceID",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(mock_print.call_args[0][0])
        self.assertEqual(payload["command"], "script-sequence")
        self.assertEqual(len(payload["result"]), 2)
        self.assertEqual(payload["result"][0]["script"], "EnterTMOD_HV")
        self.assertEqual(payload["result"][1]["script"], "GetDeviceID")

    def test_script_sequence_can_finish_with_upload(self):
        side_out = 0x02
        side_in = 0x81
        data_in = 0x83

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
                transport.queue_recv(
                    side_in,
                    b"\x0d\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00",
                )
            elif msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                transport.queue_recv(
                    side_in,
                    b"\x0d\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                )
                transport.queue_recv(data_in, b"\x11\x22")
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF):
                transport.queue_recv(
                    side_in,
                    b"\x0d\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00",
                )

        transport = FakeTransport(on_send=on_send)

        with patch("mchp_ri4.ri4_debug_cli._discover_pid", return_value=0x9012), patch(
            "mchp_ri4.ri4_debug_cli.PyusbTransport", return_value=transport
        ), patch(
            "mchp_ri4.ri4_debug_cli.resolve_repo_scripts_path", return_value=r"c:\\repo\\scripts.yaml.gz"
        ), patch(
            "mchp_ri4.ri4_debug_cli.DeviceFile.from_xml_path"
        ) as mock_device_file, patch("builtins.print") as mock_print:
            def get_script(name: str):
                payload = b"\x39\x01" if name != "ReadProgmem" else b"\xAA\x55"
                return SimpleNamespace(method=name, getData=lambda payload=payload: payload)

            mock_device_file.return_value.getScriptBasic.side_effect = get_script
            exit_code = main(
                [
                    "--tool",
                    "pk4",
                    "--timeout-ms",
                    "1000",
                    "script-sequence",
                    "--processor",
                    "dsPIC30F5011",
                    "--family",
                    "DSPIC30F",
                    "--script-name",
                    "SetSpeedFromDevice",
                    "--script-name",
                    "EnterTMOD_HV",
                    "--upload-script-name",
                    "ReadProgmem",
                    "--upload-length",
                    "2",
                    "--upload-param",
                    "0",
                    "--upload-param",
                    "2",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(mock_print.call_args[0][0])
        self.assertEqual(payload["uploadResult"]["script"], "ReadProgmem")
        self.assertEqual(payload["uploadResult"]["dataHex"], "1122")


if __name__ == "__main__":
    unittest.main()