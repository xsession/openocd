import unittest

from mchp_ri4.device_file import DeviceFile
from zephyr_pickit4_replacement.tools.gen_stub_scripts_xml import build_family_stub_scripts, render_scripts_xml


class TestZephyrStubScriptsXml(unittest.TestCase):
    def test_pic18_stub_contains_core_scripts(self):
        scripts = build_family_stub_scripts("PIC18")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["EnterDebugMode"][:2], [0x5A, 0xA5])
        self.assertEqual(by_name["WriteProgmem"][2], 0x21)
        self.assertIn("ReadProgmem", by_name)

    def test_pic16_enhanced_stub_maps_testmem_and_config_scripts(self):
        scripts = build_family_stub_scripts("PIC16Enhanced")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["WriteConfigmemDE"][2], 0x21)
        self.assertEqual(by_name["ReadProgmemDE"][2], 0x22)
        self.assertEqual(by_name["EraseTestmemRange"][2], 0x20)

    def test_dspic33a_stub_maps_de_program_memory_scripts(self):
        scripts = build_family_stub_scripts("DSPIC33A")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["WriteProgmemDE"][2], 0x21)
        self.assertEqual(by_name["ReadProgmemDE"][2], 0x22)
        self.assertIn("EnterTMOD_LV", by_name)

    def test_dspic30f_stub_maps_pe_program_memory_scripts(self):
        scripts = build_family_stub_scripts("DSPIC30F")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["WriteProgmemPE"][2], 0x21)
        self.assertEqual(by_name["ReadProgmemPE"][2], 0x22)
        self.assertIn("EnterTMOD_PE", by_name)

    def test_dspic33fj_stub_maps_pe_program_memory_scripts(self):
        scripts = build_family_stub_scripts("DSPIC33FJ")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["WriteProgmemPE"][2], 0x21)
        self.assertEqual(by_name["ReadProgmemPE"][2], 0x22)
        self.assertIn("EnterTMOD_PE", by_name)

    def test_avr_stub_maps_progmode_scripts(self):
        scripts = build_family_stub_scripts("AVR")
        by_name = {entry["name"]: entry["bytes"] for entry in scripts}
        self.assertEqual(by_name["EnterProgModeHvSp"][2], 0x30)
        self.assertEqual(by_name["ExitProgMode"][2], 0x31)
        self.assertEqual(by_name["EnterDebugModeHvSp"][2], 0x10)

    def test_rendered_xml_loads_via_device_file(self):
        xml_text = render_scripts_xml("PIC18F_STUB", build_family_stub_scripts("PIC18"))
        device_file = DeviceFile.from_xml_text("PIC18F_STUB", xml_text)
        self.assertIsNotNone(device_file.getScriptBasic("EnterDebugMode"))
        self.assertEqual(device_file.getScript("WriteProgmem").getData(), bytes([0x5A, 0xA5, 0x21]))


if __name__ == "__main__":
    unittest.main()