import argparse
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from mchp_openocd.query_bridge import (
    _build_parser,
    build_list_families_request,
    build_end_session_request,
    build_program_hex_request,
    build_probe_tool_request,
    build_read_program_request,
    build_run_script_request,
    build_start_session_request,
    load_batch_requests,
    send_batch_requests,
    send_request,
)


class _FakeSocket:
    def __init__(self, response_bytes: bytes):
        self.response_bytes = response_bytes
        self.sent = b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def sendall(self, payload: bytes) -> None:
        self.sent += payload

    def makefile(self, mode: str):
        return io.BytesIO(self.response_bytes)


class TestOpenOcdQueryBridge(unittest.TestCase):
    def test_build_list_families_request(self):
        args = argparse.Namespace(
            search_prefix="ProgrammerPIC32",
            capability=["target-vpp-control"],
            signature=["vpp-operational-value"],
            group=["power"],
            capability_match="all",
            signature_match="any",
            group_match="all",
        )
        request = build_list_families_request(args)
        self.assertEqual(request["command"], "listFamilies")
        self.assertEqual(request["args"]["searchPrefix"], "ProgrammerPIC32")
        self.assertEqual(request["args"]["capabilities"], ["target-vpp-control"])
        self.assertEqual(request["args"]["signatures"], ["vpp-operational-value"])
        self.assertEqual(request["args"]["groups"], ["power"])
        self.assertEqual(request["args"]["capabilityMatch"], "all")
        self.assertEqual(request["args"]["groupMatch"], "all")
        self.assertNotIn("signatureMatch", request["args"])

    def test_build_probe_tool_request(self):
        args = argparse.Namespace(
            tool="pk4",
            vid="0x04D8",
            pid="0x9012",
            key=["Commands in progress", "Target VDD"],
        )
        request = build_probe_tool_request(args)
        self.assertEqual(
            request,
            {
                "command": "probeTool",
                "args": {
                    "tool": "pk4",
                    "vid": "0x04D8",
                    "pid": "0x9012",
                    "keys": ["Commands in progress", "Target VDD"],
                },
            },
        )

    def test_build_start_session_request(self):
        args = argparse.Namespace(
            tool="icd4",
            vid="0x04D8",
            pid="0x9036",
            processor="PIC32MZ2048EFH",
            scripts_path="scripts.xml",
            tool_scripts_path="tool.xml",
            script_suffix="Debugger",
            pc_bytes=8,
            family="PIC32MZ",
        )
        request = build_start_session_request(args)
        self.assertEqual(request["command"], "startSession")
        self.assertEqual(request["args"]["toolScriptsPath"], "tool.xml")
        self.assertEqual(request["args"]["pcBytes"], 8)
        self.assertEqual(request["args"]["family"], "PIC32MZ")

    def test_build_program_hex_request(self):
        args = argparse.Namespace(path="firmware.hex", erase_first=False, verify=True)
        request = build_program_hex_request(args)
        self.assertEqual(
            request,
            {
                "command": "programHex",
                "args": {"path": "firmware.hex", "eraseFirst": False, "verify": True},
            },
        )

    def test_build_end_session_request(self):
        args = argparse.Namespace()
        self.assertEqual(build_end_session_request(args), {"command": "endSession", "args": {}})

    def test_build_run_script_request(self):
        args = argparse.Namespace(
            name="EnterDebugMode",
            param=["0x10", "true", "plain"],
            timeout_ms=50,
            upload_length=None,
            download_hex=None,
        )
        request = build_run_script_request(args)
        self.assertEqual(
            request,
            {
                "command": "runScript",
                "args": {
                    "name": "EnterDebugMode",
                    "params": [16, True, "plain"],
                    "timeoutMs": 50,
                },
            },
        )

    def test_build_read_program_request(self):
        args = argparse.Namespace(address=0x1000, size=0x20)
        request = build_read_program_request(args)
        self.assertEqual(
            request,
            {"command": "readProgram", "args": {"address": 0x1000, "size": 0x20}},
        )

    def test_parser_normalizes_hex_arguments(self):
        parser = _build_parser()
        args = parser.parse_args(["set-pc", "--address", "0x40"])
        args.build_request(args)
        self.assertEqual(args.address, "0x40")

    def test_load_batch_requests(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            json.dump(
                {
                    "stopOnError": False,
                    "variables": {"PROC": "PIC32MZ2048EFH"},
                    "requests": [{"command": "startSession", "args": {"processor": "${PROC}"}}],
                },
                handle,
            )
            path = handle.name

        requests, stop_on_error = load_batch_requests(path, ["PROC=PIC16F1509", "VID=0x04D8"])

        self.assertFalse(stop_on_error)
        self.assertEqual(requests, [{"command": "startSession", "args": {"processor": "PIC16F1509"}}])

    def test_send_batch_requests_stops_on_error(self):
        with patch(
            "mchp_openocd.query_bridge.send_request",
            side_effect=[{"ok": True, "result": {}}, {"ok": False, "error": "bad"}, {"ok": True, "result": {}}],
        ) as send:
            responses = send_batch_requests(
                "127.0.0.1",
                9123,
                [{"command": "ping", "args": {}}, {"command": "run", "args": {}}, {"command": "halt", "args": {}}],
            )

        self.assertEqual(len(responses), 2)
        self.assertEqual(send.call_count, 2)

    def test_send_request_round_trip(self):
        fake_socket = _FakeSocket(b'{"ok": true, "result": []}\n')
        with patch("mchp_openocd.query_bridge.socket.create_connection", return_value=fake_socket):
            response = send_request("127.0.0.1", 9123, {"command": "listFamilies", "args": {}})
        self.assertTrue(response["ok"])
        self.assertIn(b'"command": "listFamilies"', fake_socket.sent)


if __name__ == "__main__":
    unittest.main()