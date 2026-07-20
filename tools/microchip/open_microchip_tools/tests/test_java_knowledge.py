import unittest

from mchp_ri4.family_profiles import FAMILY_PROFILES, JAVA_DEVICE_FAMILIES
from mchp_ri4.java_knowledge import dump_java_ri4_knowledge, load_java_ri4_knowledge


class TestJavaKnowledge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = load_java_ri4_knowledge()

    def test_dispatch_covers_every_known_family(self):
        families = {family.family for family in self.knowledge.families}
        self.assertEqual(families, set(JAVA_DEVICE_FAMILIES))

    def test_profiles_match_java_dispatch_classes(self):
        for family_name, profile in FAMILY_PROFILES.items():
            family = self.knowledge.get_family(family_name)
            self.assertIsNotNone(family)
            self.assertEqual(profile.programmer_class, family.programmer_class)
            self.assertEqual(profile.debugger_class, family.debugger_class)

    def test_inherited_debugger_scripts_are_transcoded(self):
        family = self.knowledge.get_family("PIC32MZ")
        self.assertIsNotNone(family)
        self.assertIn("Run", family.all_script_names())
        self.assertIn("SetPC", family.all_script_names())
        self.assertIn("WriteProgmemPE", family.all_script_names())

    def test_avr_debugger_keeps_family_specific_scripts(self):
        family = self.knowledge.get_family("AVR")
        self.assertIsNotNone(family)
        self.assertIn("EnterDebugModeHvSp", family.debugger_scripts)
        self.assertIn("WriteOcdProgmem", family.debugger_scripts)
        self.assertIn("SetHWBP", family.debugger_scripts)

    def test_helper_method_selected_scripts_are_resolved(self):
        programmer_16 = self.knowledge.get_class("Programmer16Enhanced")
        programmer_18e = self.knowledge.get_class("Programmer18Enhanced")
        self.assertIsNotNone(programmer_16)
        self.assertIsNotNone(programmer_18e)
        self.assertIn("WriteConfigmemDE", programmer_16.direct_script_names())
        self.assertIn("WriteTestmem", programmer_18e.direct_script_names())

    def test_raw_command_references_are_tracked_separately(self):
        programmer = self.knowledge.get_class("Programmer")
        debugger = self.knowledge.get_class("Debugger")
        self.assertIsNotNone(programmer)
        self.assertIsNotNone(debugger)
        self.assertIn("holdInResetScript", programmer.direct_raw_command_refs())
        self.assertIn("GET_RUNTIME_DATA_COMMAND", debugger.direct_raw_command_refs())

    def test_raw_command_semantics_include_opcode_and_tags(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "holdInResetScript"
        )
        self.assertEqual(invocation.opcode_byte, 0xB1)
        self.assertIn("reset", invocation.semantic_tags)
        self.assertIn("opcode:B1", invocation.semantic_tags)
        self.assertEqual(invocation.taxonomy_group, "reset")
        self.assertEqual(invocation.taxonomy_action, "assert")
        self.assertIn("target-reset-control", invocation.capability_tags)

    def test_static_field_byte_array_commands_are_decoded(self):
        debugger = self.knowledge.get_class("Debugger")
        self.assertIsNotNone(debugger)
        invocation = next(
            raw
            for method in debugger.methods
            for raw in method.raw_command_invocations
            if raw.reference == "GET_RUNTIME_DATA_COMMAND"
        )
        self.assertEqual(invocation.byte_values, (30, -128))
        self.assertEqual(invocation.opcode_byte, 0x1E)
        self.assertEqual(invocation.signature_name, "runtime-data-query")
        self.assertIn("signature:runtime-data-query", invocation.semantic_tags)

    def test_opcode_family_fallback_applies_to_unclassified_reference(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "scriptContent"
        )
        self.assertEqual(invocation.opcode_byte, 0xEF)
        self.assertEqual(invocation.taxonomy_group, "tool-config")
        self.assertEqual(invocation.taxonomy_action, "payload")
        self.assertIn("tool-script-payload", invocation.capability_tags)

    def test_signature_recognition_distinguishes_composite_reset_sequence(self):
        programmer = self.knowledge.get_class("ProgrammerEfc6450")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "releaseFromResetScript"
        )
        self.assertEqual(invocation.signature_name, "reset-cycle-release")
        self.assertEqual(invocation.taxonomy_group, "reset")
        self.assertEqual(invocation.taxonomy_action, "cycle-release")
        self.assertIn("signature:reset-cycle-release", invocation.semantic_tags)
        self.assertIn("target-reset-pulse", invocation.capability_tags)

    def test_signature_recognition_handles_dynamic_led_payload(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "setLedBrightness"
        )
        self.assertEqual(invocation.signature_name, "tool-led-brightness")
        self.assertEqual(invocation.taxonomy_group, "tool-config")
        self.assertEqual(invocation.taxonomy_action, "led-brightness")
        self.assertIn("signature:tool-led-brightness", invocation.semantic_tags)
        self.assertIn("tool-led-control", invocation.capability_tags)

    def test_signature_recognition_handles_power_hold_toggles(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocations = [
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "setSelMaintainActivePower"
        ]
        signature_names = {raw.signature_name for raw in invocations}
        capability_sets = {capability for raw in invocations for capability in raw.capability_tags}
        self.assertEqual(signature_names, {"power-maintain-active-enable", "power-maintain-active-disable"})
        self.assertIn("target-power-hold", capability_sets)

    def test_multiline_power_init_script_is_decoded(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "initPowerScript"
        )
        self.assertEqual(invocation.opcode_byte, 0x40)
        self.assertEqual(invocation.signature_name, "power-init-sequence")
        self.assertEqual(invocation.taxonomy_group, "power")
        self.assertEqual(invocation.taxonomy_action, "init-sequence")
        self.assertIn("target-vpp-control", invocation.capability_tags)

    def test_reassigned_power_source_script_keeps_branch_alternatives(self):
        programmer = self.knowledge.get_class("Programmer")
        self.assertIsNotNone(programmer)
        invocations = [
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "powerTargetFromToolScript"
        ]
        signature_names = {raw.signature_name for raw in invocations}
        self.assertEqual(signature_names, {"power-target-from-tool-enable", "power-target-from-tool-disable"})

    def test_single_byte_vpp_command_is_classified(self):
        programmer = self.knowledge.get_class("Programmer16Enhanced")
        self.assertIsNotNone(programmer)
        invocation = next(
            raw
            for method in programmer.methods
            for raw in method.raw_command_invocations
            if raw.reference == "setVppToOperationalValue"
        )
        self.assertEqual(invocation.signature_name, "vpp-operational-value")
        self.assertIn("target-vpp-control", invocation.capability_tags)

    def test_json_dump_contains_family_and_class_sections(self):
        payload = dump_java_ri4_knowledge()
        self.assertIn('"families"', payload)
        self.assertIn('"classes"', payload)
        self.assertIn('"PIC32MZ"', payload)


if __name__ == "__main__":
    unittest.main()