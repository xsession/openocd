import unittest

from mchp_ri4.family_profiles import FAMILY_PROFILES, JAVA_DEVICE_FAMILIES, family_inventory, get_family_profile


class TestFamilyProfiles(unittest.TestCase):
    def test_every_java_family_has_profile(self):
        self.assertEqual(sorted(JAVA_DEVICE_FAMILIES), sorted(FAMILY_PROFILES.keys()))

    def test_inventory_contains_all_known_families(self):
        families = {entry["family"] for entry in family_inventory()}
        self.assertEqual(families, set(JAVA_DEVICE_FAMILIES))

    def test_lookup_is_case_insensitive(self):
        profile = get_family_profile("pic32mz")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.family, "PIC32MZ")

    def test_generated_profiles_keep_named_script_candidates_only(self):
        pic32 = get_family_profile("PIC32MZ")
        self.assertIsNotNone(pic32)
        self.assertEqual(pic32.program_entry_scripts, ("EnterTMOD_LV", "InitJTAG", "SetupSerialMode", "LoadLoader", "DownloadPE", "TestPEConnect"))

    def test_generated_profiles_include_java_selected_debug_exec_scripts(self):
        pic16 = get_family_profile("PIC16Enhanced")
        pic18e = get_family_profile("PIC18FEnhanced")
        self.assertIsNotNone(pic16)
        self.assertIsNotNone(pic18e)
        self.assertIn("WriteConfigmemDE", pic16.write_program_scripts)
        self.assertIn("WriteTestmem", pic18e.write_program_scripts)

    def test_family_inventory_contains_knowledge_metadata(self):
        pic32 = next(entry for entry in family_inventory() if entry["family"] == "PIC32MZ")
        self.assertIn("ProgrammerPIC32MZ", pic32["programmerLineage"])
        self.assertIn("programmerRawCommands", pic32)
        self.assertIn("programmerRawCommandTags", pic32)
        self.assertIn("programmerRawCommandCapabilities", pic32)
        self.assertIn("programmerRawCommandSignatures", pic32)
        self.assertTrue(pic32["supportsDebugging"])

    def test_family_inventory_can_filter_by_capability_any(self):
        families = family_inventory(required_capabilities=["target-vpp-control"])
        self.assertTrue(families)
        self.assertIn("PIC16Enhanced", {entry["family"] for entry in families})

    def test_family_inventory_can_filter_by_capability_all(self):
        families = family_inventory(
            required_capabilities=["target-reset-pulse", "target-vpp-control"],
            capability_match="all",
        )
        self.assertIn("EFC_6450", {entry["family"] for entry in families})
        self.assertNotIn("PIC16Enhanced", {entry["family"] for entry in families})

    def test_family_inventory_can_filter_by_signature(self):
        families = family_inventory(required_signatures=["vpp-operational-value"])
        self.assertIn("PIC16Enhanced", {entry["family"] for entry in families})

    def test_family_inventory_can_filter_by_group(self):
        families = family_inventory(required_groups=["trace"])
        self.assertTrue(families)
        for entry in families:
            groups = set(entry["programmerRawCommandGroups"]) | set(entry["debuggerRawCommandGroups"])
            self.assertIn("trace", groups)

    def test_family_inventory_can_filter_by_search_prefix(self):
        families = family_inventory(search_prefix="ProgrammerPIC32")
        self.assertTrue(families)
        for entry in families:
            self.assertTrue(
                entry["family"].lower().startswith("programmerpic32")
                or entry["programmerClass"].lower().startswith("programmerpic32")
                or entry["debuggerClass"].lower().startswith("programmerpic32")
            )


if __name__ == "__main__":
    unittest.main()