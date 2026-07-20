import unittest

from zephyr_pickit4_replacement.tools.gen_ri4_catalog import build_catalog_entries, render_header


class TestZephyrPickit4Catalog(unittest.TestCase):
    def test_catalog_entries_include_pic32mz(self):
        entries = build_catalog_entries()
        pic32mz = next(entry for entry in entries if entry["family"] == "PIC32MZ")
        self.assertEqual(pic32mz["behavior"], "pic32_pe")
        self.assertIn("EnterDebugMode", pic32mz["scripts"])
        self.assertTrue(pic32mz["supportsProgramming"])

    def test_render_header_contains_family_table(self):
        header = render_header([
            {
                "family": "PIC16",
                "behavior": "pic16_enhanced",
                "supportsProgramming": True,
                "supportsDebugging": True,
                "supportsSetPc": True,
                "scripts": ["EnterDebugMode", "GetPC"],
            }
        ])
        self.assertIn("ri4_family_scripts_0", header)
        self.assertIn('"PIC16"', header)
        self.assertIn("ri4_family_catalog_count", header)



if __name__ == "__main__":
    unittest.main()