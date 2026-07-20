import unittest
from unittest.mock import patch

from mchp_openocd.bridge_server import BridgeError, BridgeProtocol, BridgeState


class TestOpenOcdBridgeProtocol(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = BridgeProtocol(BridgeState())

    def test_list_families(self):
        response = self.protocol.handle({"command": "listFamilies", "args": {}})
        self.assertTrue(response["ok"])
        self.assertGreaterEqual(len(response["result"]), 28)
        pic32 = next(entry for entry in response["result"] if entry["family"] == "PIC32MZ")
        self.assertIn("programmerLineage", pic32)
        pic16e = next(entry for entry in response["result"] if entry["family"] == "PIC16Enhanced")
        self.assertIn("target-vpp-control", pic16e["programmerRawCommandCapabilities"])
        self.assertIn("vpp-operational-value", pic16e["programmerRawCommandSignatures"])

    def test_list_families_can_filter_by_capability(self):
        response = self.protocol.handle(
            {"command": "listFamilies", "args": {"capabilities": ["target-vpp-control"]}}
        )
        self.assertTrue(response["ok"])
        families = {entry["family"] for entry in response["result"]}
        self.assertIn("PIC16Enhanced", families)
        self.assertTrue(response["result"])
        for entry in response["result"]:
            capabilities = set(entry["programmerRawCommandCapabilities"]) | set(entry["debuggerRawCommandCapabilities"])
            self.assertIn("target-vpp-control", capabilities)

    def test_list_families_can_require_all_capabilities(self):
        response = self.protocol.handle(
            {
                "command": "listFamilies",
                "args": {
                    "capabilities": ["target-vpp-control", "target-reset-pulse"],
                    "capabilityMatch": "all",
                },
            }
        )
        self.assertTrue(response["ok"])
        families = {entry["family"] for entry in response["result"]}
        self.assertIn("EFC_6450", families)
        self.assertNotIn("PIC16Enhanced", families)

    def test_list_families_can_filter_by_signature(self):
        response = self.protocol.handle(
            {"command": "listFamilies", "args": {"signatures": ["vpp-operational-value"]}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            signatures = set(entry["programmerRawCommandSignatures"]) | set(entry["debuggerRawCommandSignatures"])
            self.assertIn("vpp-operational-value", signatures)

    def test_list_families_can_filter_by_group(self):
        response = self.protocol.handle(
            {"command": "listFamilies", "args": {"groups": ["trace"]}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            groups = set(entry["programmerRawCommandGroups"]) | set(entry["debuggerRawCommandGroups"])
            self.assertIn("trace", groups)

    def test_list_families_can_filter_by_search_prefix(self):
        response = self.protocol.handle(
            {"command": "listFamilies", "args": {"searchPrefix": "ProgrammerPIC32"}}
        )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"])
        for entry in response["result"]:
            self.assertTrue(
                entry["family"].lower().startswith("programmerpic32")
                or entry["programmerClass"].lower().startswith("programmerpic32")
                or entry["debuggerClass"].lower().startswith("programmerpic32")
            )

    def test_start_session_dispatch(self):
        with patch("mchp_openocd.bridge_server.NamedScriptSession") as session_type:
            session = session_type.open_usb.return_value
            session.script_inventory.return_value = {"family": "PIC32MZ", "tool": "PK4"}
            response = self.protocol.handle(
                {
                    "command": "startSession",
                    "args": {
                        "tool": "pk4",
                        "vid": "0x04D8",
                        "pid": "0x9012",
                        "family": "PIC32MZ",
                        "processor": "PIC32MZ2048EFH",
                        "scriptsPath": "scripts.xml",
                    },
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["family"], "PIC32MZ")

    def test_end_session_closes_active_session(self):
        session = self.protocol._state.session = unittest.mock.Mock()
        session.script_inventory.return_value = {"family": "PIC32MZ", "tool": "PK4"}

        response = self.protocol.handle({"command": "endSession", "args": {}})

        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["closed"])
        self.assertEqual(response["result"]["previousSession"]["family"], "PIC32MZ")
        session.close.assert_called_once_with()
        self.assertIsNone(self.protocol._state.session)

    def test_start_session_replaces_existing_session(self):
        existing = self.protocol._state.session = unittest.mock.Mock()
        existing.script_inventory.return_value = {"family": "PIC16Enhanced", "tool": "PK4"}
        with patch("mchp_openocd.bridge_server.NamedScriptSession") as session_type:
            session = session_type.open_usb.return_value
            session.script_inventory.return_value = {"family": "PIC32MZ", "tool": "PK4"}

            response = self.protocol.handle(
                {
                    "command": "startSession",
                    "args": {
                        "tool": "pk4",
                        "vid": "0x04D8",
                        "pid": "0x9012",
                        "family": "PIC32MZ",
                        "processor": "PIC32MZ2048EFH",
                        "scriptsPath": "scripts.xml",
                    },
                }
            )

        self.assertTrue(response["ok"])
        existing.close.assert_called_once_with()

    def test_target_status_and_debug_resource_dispatch(self):
        session = self.protocol._state.session = unittest.mock.Mock()
        session.target_status.return_value = {"state": "halted", "running": False, "pc": 0x1234}
        session.add_breakpoint.return_value = {"slot": 0, "address": 0x1234}
        session.add_watchpoint.return_value = {"slot": 1, "address": 0x2000}

        status = self.protocol.handle(
            {"command": "targetStatus", "args": {"refresh": True, "includePc": True}}
        )
        bp = self.protocol.handle(
            {"command": "addBreakpoint", "args": {"address": "0x1234", "kind": 2}}
        )
        wp = self.protocol.handle(
            {
                "command": "addWatchpoint",
                "args": {"address": "0x2000", "length": 4, "access": "write"},
            }
        )

        self.assertEqual(status["result"]["state"], "halted")
        self.assertEqual(bp["result"]["slot"], 0)
        self.assertEqual(wp["result"]["slot"], 1)
        session.target_status.assert_called_once_with(refresh=True, include_pc=True)
        session.add_breakpoint.assert_called_once_with(0x1234, kind=2, slot=None)
        session.add_watchpoint.assert_called_once_with(0x2000, length=4, access="write", slot=None)

    def test_start_session_forwards_serial_and_reset_policy(self):
        with patch("mchp_openocd.bridge_server.NamedScriptSession") as session_type:
            session_type.open_usb.return_value.script_inventory.return_value = {"tool": "PK4"}
            response = self.protocol.handle(
                {
                    "command": "startSession",
                    "args": {
                        "tool": "pk4",
                        "vid": "0x04D8",
                        "pid": "0x9012",
                        "processor": "PIC18F_TEST",
                        "family": "PIC18",
                        "scriptsPath": "scripts.xml",
                        "serialNumber": "PK4-123",
                        "resetDevice": False,
                    },
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(session_type.open_usb.call_args.kwargs["serial_number"], "PK4-123")
        self.assertFalse(session_type.open_usb.call_args.kwargs["reset_device"])

    def test_probe_tool_always_closes_driver(self):
        driver = unittest.mock.Mock()
        driver.get_status_value.side_effect = RuntimeError("probe failed")
        with patch("mchp_openocd.bridge_server._tool_driver", return_value=driver):
            with self.assertRaisesRegex(RuntimeError, "probe failed"):
                self.protocol.handle(
                    {
                        "command": "probeTool",
                        "args": {"tool": "pk4", "vid": "0x04D8", "pid": "0x9012"},
                    }
                )
        driver.close.assert_called_once_with()

    def test_run_script_dispatches_basic_script(self):
        session = self.protocol._state.session = unittest.mock.Mock()
        session.run_script.return_value = {"script": "EnterDebugMode", "status": 0, "payloadHex": ""}

        response = self.protocol.handle(
            {"command": "runScript", "args": {"name": "EnterDebugMode", "params": [1, "two"], "timeoutMs": 10}}
        )

        self.assertTrue(response["ok"])
        session.run_script.assert_called_once_with("EnterDebugMode", 1, "two", timeout_ms=10)

    def test_run_script_dispatches_upload(self):
        session = self.protocol._state.session = unittest.mock.Mock()
        session.run_script_with_upload.return_value = b"\xAA\x55"

        response = self.protocol.handle(
            {"command": "runScript", "args": {"name": "GetPC", "uploadLength": 2, "params": [0, 2]}}
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["payloadHex"], "aa55")

    def test_run_script_rejects_upload_and_download_together(self):
        with self.assertRaisesRegex(BridgeError, "cannot be used together"):
            self.protocol.handle(
                {"command": "runScript", "args": {"name": "Bad", "uploadLength": 2, "downloadHex": "AA55"}}
            )