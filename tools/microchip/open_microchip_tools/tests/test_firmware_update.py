import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mchp_ri4.firmware_update import (
    PK4_PFM_START,
    _build_pk4_pfm_image,
    _parse_jam_entries,
    assess_firmware_state,
    parse_firmware_info_response,
    probe_tool_firmware,
)
from mchp_ri4.repo_assets import iter_repo_firmware_packages


class TestFirmwareUpdate(unittest.TestCase):
    def test_parse_native_firmware_info_app_mode(self):
        response = bytearray(512)
        response[1] = 0xAF
        response[3:6] = bytes((0x01, 0x00, 0x02))
        response[164:167] = bytes((0x00, 0x10, 0x00))
        response[18:22] = (0x12345678).to_bytes(4, "little")
        response[203:207] = (0x89ABCDEF).to_bytes(4, "little")
        response[219:223] = (1265202276).to_bytes(4, "little")
        response[227:231] = (1179402836).to_bytes(4, "little")
        info = parse_firmware_info_response(bytes(response))
        self.assertFalse(info.boot_mode)
        self.assertEqual(info.application_version, "01.00.02")
        self.assertEqual(info.boot_version, "00.10.00")
        self.assertTrue(info.hardware_bootloader_update_supported)

    def test_assess_firmware_state_recommends_update_on_version_mismatch(self):
        with patch("mchp_ri4.firmware_update.resolve_repo_firmware_path", return_value=Path("C:/repo/vendor/PK4FW_001000.jam")):
            state = assess_firmware_state(
                "pk4",
                {
                    "MajorFirmwareVersion": "0x0",
                    "MinorFirmwareVersion": "0xFF",
                    "MajorFirmwareVersionOnDisk": "0x1",
                    "MinorFirmwareVersionOnDisk": "0x00",
                    "HardwareRevision": "2",
                    "Commands in progress": "0",
                },
            )
        self.assertEqual(state.state, "update-recommended")
        self.assertEqual(state.recommendation, "apply-vendored-firmware-on-next-connect")

    def test_assess_firmware_state_recovery_when_boot_mode_detected(self):
        response = bytearray(512)
        response[1] = 0xBF
        response[3:6] = bytes((0x01, 0x00, 0x00))
        response[172:175] = bytes((0x01, 0x00, 0x00))
        native_info = parse_firmware_info_response(bytes(response))
        with patch("mchp_ri4.firmware_update.resolve_repo_firmware_path", return_value=Path("C:/repo/vendor/PK4FW_001000.jam")):
            state = assess_firmware_state(
                "pk4",
                {
                    "MajorFirmwareVersion": "0x1",
                    "MinorFirmwareVersion": "0x00",
                    "MajorFirmwareVersionOnDisk": "0x1",
                    "MinorFirmwareVersionOnDisk": "0x00",
                    "HardwareRevision": "2",
                    "Commands in progress": "0",
                },
                native_info=native_info,
            )
        self.assertEqual(state.state, "bootloader-mode")
        self.assertEqual(state.recommendation, "use-vendored-recovery-firmware")

    def test_assess_firmware_state_reports_comm_failure(self):
        with patch("mchp_ri4.firmware_update.resolve_repo_firmware_path", return_value=Path("C:/repo/vendor/ICD4FW_001000.jam")):
            state = assess_firmware_state("icd4", None, error="USB read failed")
        self.assertFalse(state.reachable)
        self.assertEqual(state.state, "communication-failed")
        self.assertIn("USB read failed", state.reason)

    def test_probe_tool_firmware_reads_status_keys(self):
        class FakeDriver:
            def __init__(self):
                self.closed = False

            def get_status_value(self, key: str) -> str:
                values = {
                    "MajorFirmwareVersion": "0x1",
                    "MinorFirmwareVersion": "0x00",
                    "MajorFirmwareVersionOnDisk": "0x1",
                    "MinorFirmwareVersionOnDisk": "0x00",
                    "HardwareRevision": "3",
                    "Commands in progress": "0",
                }
                return values[key]

            def close(self):
                self.closed = True

        fake_driver = FakeDriver()
        with patch("mchp_ri4.firmware_update._open_driver", return_value=fake_driver), patch(
            "mchp_ri4.firmware_update.resolve_repo_firmware_path", return_value=Path("C:/repo/vendor/PK4FW_001000.jam")
        ), patch("mchp_ri4.firmware_update.read_native_firmware_info", return_value=None):
            state = probe_tool_firmware("pk4", 0x04D8, 0x9012)
        self.assertTrue(fake_driver.closed)
        self.assertTrue(state.reachable)
        self.assertEqual(state.current_version, "1.00")

    def test_iter_repo_firmware_packages_lists_jam_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jam_dir = base / "PICkit4_TP" / "2.12.2541" / "firmware"
            jam_dir.mkdir(parents=True)
            (jam_dir / "PK4FW_001000.jam").write_text("jam", encoding="utf-8")
            packages = iter_repo_firmware_packages(base=base)
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["firmwareVersion"], "001000")

    def test_parse_jam_entries_reads_pk4_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            jam = Path(tmp) / "PK4FW_001000.jam"
            jam.write_text("boot.hex,010000\napp1 020515, 0040C000\n", encoding="utf-8")
            entries = _parse_jam_entries(jam)
        self.assertEqual(entries["boot.hex"], "010000")
        self.assertEqual(entries["app1"], "020515")
        self.assertEqual(entries["app1 020515"], "0040C000")

    def test_build_pk4_pfm_image_pads_and_appends_crc(self):
        with tempfile.TemporaryDirectory() as tmp:
            hex_path = Path(tmp) / "app.hex"
            hex_path.write_text(
                "\n".join(
                    (
                        ":020000040040BA",
                        ":04C000001122334492",
                        ":00000001FF",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            start_address, image, expected_crc = _build_pk4_pfm_image(hex_path)
        self.assertEqual(start_address, PK4_PFM_START)
        self.assertEqual(image[:4], bytes((0x11, 0x22, 0x33, 0x44)))
        self.assertEqual(len(image), 0x1F4000)
        self.assertEqual(int.from_bytes(image[-4:], "little"), expected_crc)


if __name__ == "__main__":
    unittest.main()