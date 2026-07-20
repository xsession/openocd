import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mchp_ri4.hardware_roundtrip_cli import main
from mchp_ri4.transport import FakeTransport


class TestHardwareRoundtripCli(unittest.TestCase):
    def test_trace_output_writes_error_payload_on_failure(self):
        side_out = 0x02

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == side_out:
                raise RuntimeError("boom")

        transport = FakeTransport(on_send=on_send)

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.json"
            output_path = Path(tmpdir) / "dump.hex"

            with patch("mchp_ri4.hardware_roundtrip_cli.PyusbTransport", return_value=transport), patch(
                "mchp_ri4.hardware_roundtrip_cli.DeviceFile.from_xml_path"
            ) as mock_device_file, patch("builtins.print") as mock_print:
                def get_script(name: str):
                    return SimpleNamespace(method=name, getData=lambda: b"\x39\x01")

                mock_device_file.return_value.getScriptBasic.side_effect = get_script
                exit_code = main(
                    [
                        "--tool",
                        "pk4",
                        "--pid",
                        "0x9012",
                        "--family",
                        "DSPIC30F",
                        "--processor",
                        "dsPIC30F5011",
                        "--scripts",
                        r"c:\repo\scripts.yaml.gz",
                        "--start-address",
                        "0x0",
                        "--length",
                        "0x40",
                        "--output",
                        str(output_path),
                        "--no-writeback",
                        "--trace-output",
                        str(trace_path),
                    ]
                )

            trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        payload = json.loads(mock_print.call_args[0][0])
        self.assertEqual(payload["errorType"], "RuntimeError")
        self.assertEqual(payload["trace"][0]["endpoint"], "0x02")
        self.assertEqual(trace_payload["errorType"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()