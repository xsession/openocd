import tempfile
import unittest
from pathlib import Path

from zephyr_pickit4_replacement.tools.analyze_pk4_firmware import build_pk4_report


BOOT_HEX = """:020000040040BA
:1000000008DC4020AD0140002902400029024000E8
:00000001FF
"""

APP_HEX = """:020000040040BA
:10C0000060944420ADE8400091E9400091E940008F
:10C010004D6963726F6368697020546563686E6F93
:10C020006C6F677920496E636F72706F72617465A4
:10C030006457494E555342205049436B6974203411
:020000040050AA
:1000000010A94020894150008541500085415000F1
:020000045FFF9A
:0CFFF40029EB00001505020088FC58A360
:00000001FF
"""

JAM_TEXT = """boot.hex,010000
scripts.xml,001008
app1 020515, 0040C000
app2 1.15.20, 00500000
"""


class TestPk4FirmwareAnalysis(unittest.TestCase):
    def test_build_pk4_report_infers_cortex_m_and_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot = root / "boot.hex"
            app = root / "app.hex"
            jam = root / "PK4FW_001000.jam"
            boot.write_text(BOOT_HEX, encoding="utf-8")
            app.write_text(APP_HEX, encoding="utf-8")
            jam.write_text(JAM_TEXT, encoding="utf-8")

            report = build_pk4_report(boot, app, jam)

            self.assertEqual(report["boot"]["startAddress"], "0x00400000")
            self.assertEqual(report["app"]["startAddress"], "0x0040C000")
            self.assertEqual(report["boot"]["inferredArchitecture"]["name"], "arm-cortex-m")
            self.assertEqual(report["app"]["inferredArchitecture"]["name"], "arm-cortex-m")
            self.assertTrue(report["observations"]["bootBeforeApp"])
            self.assertEqual(report["observations"]["likelyMigrationTarget"], "arm-cortex-m-zephyr")
            self.assertIsNotNone(report["app"]["keywordOffsets"]["Microchip"])
            self.assertIsNotNone(report["app"]["keywordOffsets"]["WINUSB"])
            self.assertEqual(report["app"]["segments"][1]["start"], "0x00500000")
            self.assertEqual(report["app"]["tailRecord"]["versionWord"], "0x00020515")
            self.assertEqual(report["jam"]["slots"][1]["address"], "0x00500000")
            self.assertIn("0x00500000", report["app"]["wordReferences"])

    def test_real_vendored_pk4_images_match_observed_baseline(self):
        repo_root = Path(__file__).resolve().parents[1]
        boot = repo_root / "vendor" / "mplabx" / "tool_firmware" / "pk4" / "boot.hex"
        app = repo_root / "vendor" / "mplabx" / "tool_firmware" / "pk4" / "app.hex"
        jam = repo_root / "vendor" / "mplabx" / "tool_firmware" / "pk4" / "PK4FW_001000.jam"

        report = build_pk4_report(boot, app, jam)

        self.assertEqual(report["boot"]["startAddress"], "0x00400000")
        self.assertEqual(report["app"]["startAddress"], "0x0040C000")
        self.assertEqual(report["boot"]["vectorWords"][0], "0x2040DC08")
        self.assertEqual(report["app"]["vectorWords"][0], "0x20449460")
        self.assertEqual(report["app"]["inferredArchitecture"]["name"], "arm-cortex-m")
        self.assertEqual(report["observations"]["likelyMigrationTarget"], "arm-cortex-m-zephyr")
        self.assertEqual(report["app"]["keywordOffsets"]["PICkit 4"], 288748)
        self.assertEqual(report["app"]["keywordOffsets"]["WINUSB"], 329602)
        self.assertEqual(report["app"]["keywordOffsets"]["Microchip"], 330292)
        self.assertEqual(report["app"]["keywordOffsets"]["CMSIS"], 481007)
        self.assertTrue(report["observations"]["hasSecondaryAppCandidate"])
        self.assertTrue(report["observations"]["tailRecordMatchesBootVersion"])
        self.assertTrue(report["observations"]["tailRecordMatchesPrimaryAppVersion"])
        self.assertTrue(report["observations"]["bootReferencesPrimaryApp"])
        self.assertFalse(report["observations"]["bootReferencesSecondaryApp"])
        self.assertTrue(report["observations"]["appReferencesBothSlots"])
        self.assertTrue(report["observations"]["primaryAppReferencesSecondarySlot"])
        self.assertFalse(report["observations"]["secondaryAppReferencesPrimarySlot"])
        self.assertTrue(report["observations"]["secondaryAppSelfReferences"])
        self.assertTrue(report["observations"]["winusbOnlyInPrimaryApp"])
        self.assertTrue(report["observations"]["cmsisPresentInSecondaryApp"])
        self.assertTrue(report["observations"]["secondaryAppCarriesCmsisDapBanner"])
        self.assertEqual(report["observations"]["secondaryAppSystemControlRefs"], ["0x005041F4", "0x0051EA04", "0x005228BC"])
        self.assertTrue(report["observations"]["primarySecondaryRefLooksDescriptorLike"])
        self.assertTrue(report["observations"]["secondarySystemControlSiteLooksLiteralPoolBacked"])
        self.assertEqual(report["app"]["segments"][1]["start"], "0x00500000")
        self.assertEqual(report["app"]["segments"][1]["vectorWords"][0], "0x2040A910")
        self.assertEqual(report["app"]["segments"][1]["vectorWords"][1], "0x00504189")
        self.assertEqual(report["boot"]["tailRecord"]["versionWord"], "0x00010000")
        self.assertEqual(report["app"]["tailRecord"]["versionWord"], "0x00020515")
        self.assertEqual(report["boot"]["wordReferences"]["0x0040C000"][0], "0x00400160")
        self.assertEqual(report["boot"]["wordReferences"]["0x00500000"], [])
        self.assertEqual(report["app"]["wordReferences"]["0x00500000"][0], "0x00456864")
        self.assertEqual(report["app"]["segments"][0]["wordReferences"]["0x00500000"], ["0x00456864"])
        self.assertEqual(report["app"]["segments"][1]["wordReferences"]["0x0040C000"], [])
        self.assertIsNone(report["app"]["segments"][1]["keywordOffsets"]["WINUSB"])
        self.assertIsNotNone(report["app"]["segments"][1]["keywordOffsets"]["CMSIS"])
        self.assertEqual(report["app"]["segments"][1]["bannerOffsets"]["MPLAB PICkit 4 CMSIS-DAP"], 146536)
        self.assertEqual(report["app"]["segments"][1]["wordReferences"]["0xE000ED00"], ["0x005041F4", "0x0051EA04", "0x005228BC"])
        self.assertEqual(report["app"]["notableSites"]["0x00456864"]["words"][4]["value"], "0x00500000")
        self.assertEqual(report["app"]["notableSites"]["0x00456864"]["words"][4]["kind"], "secondarySlotBase")


if __name__ == "__main__":
    unittest.main()