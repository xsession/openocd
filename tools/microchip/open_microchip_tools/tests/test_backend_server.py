import io
import json
import unittest
from unittest.mock import patch

from mchp_vscode.backend_server import BackendServer


class TestBackendServer(unittest.TestCase):
    def _run(self, request: dict) -> dict:
        payload = {"id": 1, **request}
        stdin = io.StringIO(json.dumps(payload) + "\n")
        stdout = io.StringIO()
        server = BackendServer(stdin=stdin, stdout=stdout)
        server.serve_forever()
        return json.loads(stdout.getvalue().strip())

    def test_ping(self):
        response = self._run({"command": "ping", "args": {}})
        self.assertTrue(response["ok"])
        self.assertEqual(response["id"], 1)
        self.assertEqual(response["result"]["message"], "pong")

    def test_list_devices_dispatch(self):
        with patch("mchp_vscode.backend_server.debug_backend.list_devices", return_value=["PIC16F1509"]):
            response = self._run({"command": "listDevices", "args": {"prefix": "PIC16"}})
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"], ["PIC16F1509"])

    def test_probe_tool_dispatch(self):
        with patch("mchp_vscode.backend_server._tool_driver") as tool_driver:
            tool_driver.return_value.get_status_value.side_effect = lambda key: {"Commands in progress": "0"}[key]
            response = self._run(
                {
                    "command": "probeTool",
                    "args": {"tool": "pk4", "vid": "0x04D8", "pid": "0x9012", "keys": ["Commands in progress"]},
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["tool"], "PK4")
        self.assertEqual(response["result"]["status"]["Commands in progress"], "0")

    def test_tool_power_target_dispatch(self):
        with patch("mchp_vscode.backend_server._tool_driver") as tool_driver:
            tool_driver.return_value.power_target.return_value = {"requestedVoltageMv": 5000, "status": {"targetVddMv": 4998}}
            response = self._run(
                {
                    "command": "toolPowerTarget",
                    "args": {"tool": "pk4", "vid": "0x04D8", "pid": "0x9012", "voltageMv": 5000},
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["requestedVoltageMv"], 5000)
        self.assertEqual(response["result"]["status"]["targetVddMv"], 4998)

    def test_tool_firmware_inventory_dispatch(self):
        with patch(
            "mchp_vscode.backend_server.iter_repo_firmware_packages",
            return_value=[{"tool": "PK4", "path": "vendor/mplabx/PK4FW_001000.jam"}],
        ):
            response = self._run({"command": "toolFirmwareInventory", "args": {"tool": "pk4"}})

        self.assertTrue(response["ok"])
        self.assertEqual(len(response["result"]["packages"]), 1)
        self.assertEqual(response["result"]["packages"][0]["tool"], "PK4")

    def test_tool_probe_firmware_dispatch(self):
        with patch("mchp_vscode.backend_server.probe_tool_firmware") as probe:
            probe.return_value.to_dict.return_value = {
                "tool": "PK4",
                "reachable": False,
                "state": "communication-failed",
                "recommendation": "use-vendored-recovery-firmware",
            }
            response = self._run(
                {
                    "command": "toolProbeFirmware",
                    "args": {"tool": "pk4", "vid": "0x04D8", "pid": "0x9012"},
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["tool"], "PK4")
        self.assertEqual(response["result"]["recommendation"], "use-vendored-recovery-firmware")

    def test_list_hardware_families(self):
        response = self._run({"command": "listHardwareFamilies", "args": {}})
        self.assertTrue(response["ok"])
        self.assertGreaterEqual(len(response["result"]), 28)
        self.assertIn("PIC32MZ", {entry["family"] for entry in response["result"]})
        pic32 = next(entry for entry in response["result"] if entry["family"] == "PIC32MZ")
        self.assertIn("programmerLineage", pic32)
        self.assertIn("namedScriptCount", pic32)

    def test_list_hardware_families_can_filter_by_signature(self):
        response = self._run(
            {"command": "listHardwareFamilies", "args": {"signatures": ["vpp-operational-value"]}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            signatures = set(entry["programmerRawCommandSignatures"]) | set(entry["debuggerRawCommandSignatures"])
            self.assertIn("vpp-operational-value", signatures)

    def test_list_hardware_families_can_filter_by_group(self):
        response = self._run(
            {"command": "listHardwareFamilies", "args": {"groups": ["trace"]}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            groups = set(entry["programmerRawCommandGroups"]) | set(entry["debuggerRawCommandGroups"])
            self.assertIn("trace", groups)

    def test_list_hardware_families_can_filter_by_search_prefix(self):
        response = self._run(
            {"command": "listHardwareFamilies", "args": {"searchPrefix": "ProgrammerPIC32"}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            self.assertTrue(
                entry["family"].lower().startswith("programmerpic32")
                or entry["programmerClass"].lower().startswith("programmerpic32")
                or entry["debuggerClass"].lower().startswith("programmerpic32")
            )

    def test_hardware_start_session_dispatch(self):
        with patch("mchp_vscode.backend_server.NamedScriptSession") as session_type:
            session = session_type.open_usb.return_value
            session.script_inventory.return_value = {
                "tool": "PK4",
                "processor": "PIC16F_TEST",
                "pcBytes": 2,
                "deviceScriptCount": 6,
                "toolScriptCount": 0,
                "sampleScripts": ["EnterDebugMode"],
            }
            session.has_script.side_effect = lambda name: True
            response = self._run(
                {
                    "command": "hardwareStartSession",
                    "args": {
                        "tool": "pk4",
                        "vid": "0x04D8",
                        "pid": "0x9012",
                        "family": "PIC16",
                        "processor": "PIC16F_TEST",
                        "scriptsPath": "scripts.xml",
                        "pcBytes": 2,
                    },
                }
            )

        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["hasDebugScripts"])
        self.assertTrue(response["result"]["hasProgrammingScripts"])
        self.assertEqual(response["result"]["familyMetadata"]["family"], "PIC16")

    def test_hardware_end_session_closes_active_session(self):
        stdin = io.StringIO(json.dumps({"id": 1, "command": "hardwareEndSession", "args": {}}) + "\n")
        stdout = io.StringIO()
        server = BackendServer(stdin=stdin, stdout=stdout)
        session = server._hardware_session = unittest.mock.Mock()
        session.family = "PIC16"
        session.script_inventory.return_value = {"processor": "PIC16F_TEST", "family": "PIC16"}

        server.serve_forever()
        response = json.loads(stdout.getvalue().strip())

        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["closed"])
        self.assertEqual(response["result"]["previousSession"]["familyMetadata"]["family"], "PIC16")
        session.close.assert_called_once_with()

    def test_hardware_start_session_replaces_existing_session(self):
        stdin = io.StringIO(
            json.dumps(
                {
                    "id": 1,
                    "command": "hardwareStartSession",
                    "args": {
                        "tool": "pk4",
                        "vid": "0x04D8",
                        "pid": "0x9012",
                        "family": "PIC16",
                        "processor": "PIC16F_TEST",
                        "scriptsPath": "scripts.xml",
                        "pcBytes": 2,
                    },
                }
            )
            + "\n"
        )
        stdout = io.StringIO()
        server = BackendServer(stdin=stdin, stdout=stdout)
        existing = server._hardware_session = unittest.mock.Mock()
        existing.family = "PIC16"
        existing.script_inventory.return_value = {"processor": "OLD", "family": "PIC16"}
        with patch("mchp_vscode.backend_server.NamedScriptSession") as session_type:
            session = session_type.open_usb.return_value
            session.script_inventory.return_value = {
                "tool": "PK4",
                "processor": "PIC16F_TEST",
                "pcBytes": 2,
                "deviceScriptCount": 6,
                "toolScriptCount": 0,
                "sampleScripts": ["EnterDebugMode"],
            }
            session.has_script.side_effect = lambda name: True
            server.serve_forever()

        existing.close.assert_called_once_with()

    def test_hardware_program_hex_dispatch_requires_session(self):
        response = self._run({"command": "hardwareProgramHex", "args": {"path": "demo.hex"}})
        self.assertFalse(response["ok"])
        self.assertIn("No hardware session is active", response["error"])

    def test_run_zephyr_stub_demo_dispatch(self):
        with patch("mchp_vscode.backend_server.run_stub_demo", return_value={"family": "ARM_MPU", "status": {"Family": "ARM_MPU"}}):
            response = self._run(
                {
                    "command": "runZephyrStubDemo",
                    "args": {"family": "ARM_MPU", "processor": "ATSAME70_STUB", "writeAddress": "0x20", "writeHex": "AABB"},
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["family"], "ARM_MPU")

    def test_run_zephyr_stub_demo_rejects_bad_hex(self):
        response = self._run({"command": "runZephyrStubDemo", "args": {"writeHex": "GG"}})
        self.assertFalse(response["ok"])
        self.assertIn("writeHex must be valid hex", response["error"])


if __name__ == "__main__":
    unittest.main()