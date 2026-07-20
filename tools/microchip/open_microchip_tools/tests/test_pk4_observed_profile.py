import unittest

from zephyr_pickit4_replacement.pk4_observed_profile import (
    PK4_APP2_BASE,
    DEFAULT_STATUS_KEYS,
    PK4_APP_BASE,
    PK4_BOOT_BASE,
    PK4_PRIMARY_ROLE,
    PK4_PROFILE_NAME,
    PK4_RESET_VECTOR,
    Pk4ObservedProbeModel,
)
from zephyr_pickit4_replacement.tools.exercise_pk4_status import build_status_exercise


class TestPk4ObservedProfile(unittest.TestCase):
    def test_status_snapshot_reports_observed_profile_values(self):
        probe = Pk4ObservedProbeModel(debug_mode=True, halted=True)

        snapshot = probe.status_snapshot(DEFAULT_STATUS_KEYS)

        self.assertEqual(snapshot["Debug Mode"], "1")
        self.assertEqual(snapshot["Target Halted"], "1")
        self.assertEqual(snapshot["Program Counter"], f"0x{PK4_RESET_VECTOR:08X}")
        self.assertEqual(snapshot["Probe Profile"], PK4_PROFILE_NAME)
        self.assertEqual(snapshot["Boot Base"], f"0x{PK4_BOOT_BASE:08X}")
        self.assertEqual(snapshot["App Base"], f"0x{PK4_APP_BASE:08X}")
        self.assertEqual(snapshot["App2 Base"], f"0x{PK4_APP2_BASE:08X}")
        self.assertEqual(snapshot["Primary Role"], PK4_PRIMARY_ROLE)
        self.assertEqual(snapshot["Secondary Identity"], "MPLAB PICkit 4 CMSIS-DAP")
        self.assertEqual(snapshot["Execution Slot"], "app")
        self.assertEqual(snapshot["Execution Role"], PK4_PRIMARY_ROLE)
        self.assertEqual(snapshot["Last Program Region"], "none")
        self.assertEqual(snapshot["Architecture"], "arm-cortex-m")

    def test_address_classification_and_region_routing(self):
        probe = Pk4ObservedProbeModel()

        boot_write = probe.write_program(PK4_BOOT_BASE + 0x20, b"BOOT")
        app_write = probe.write_program(PK4_APP_BASE + 0x30, b"APP!")
        app2_write = probe.write_program(PK4_APP2_BASE + 0x10, b"CMSI")
        relative_write = probe.write_program(0x40, b"REL!")

        self.assertEqual(boot_write["region"], "boot")
        self.assertEqual(app_write["region"], "app")
        self.assertEqual(app2_write["region"], "app2")
        self.assertEqual(relative_write["region"], "app")
        self.assertEqual(probe.read_program(PK4_BOOT_BASE + 0x20, 4)["data"], b"BOOT")
        self.assertEqual(probe.read_program(PK4_APP_BASE + 0x30, 4)["data"], b"APP!")
        self.assertEqual(probe.read_program(PK4_APP2_BASE + 0x10, 4)["data"], b"CMSI")
        self.assertEqual(probe.read_program(0x40, 4)["data"], b"REL!")
        self.assertEqual(probe.get_status_value("Last Program Region"), "app")
        self.assertEqual(probe.get_status_value("Last Program Role"), PK4_PRIMARY_ROLE)

    def test_execution_slot_switches_with_program_counter(self):
        probe = Pk4ObservedProbeModel(pc=PK4_APP2_BASE + 0x100, debug_mode=True, halted=True)

        self.assertEqual(probe.get_status_value("Execution Slot"), "app2")
        self.assertEqual(probe.get_status_value("Execution Role"), "CMSIS-DAP control/update slot")

    def test_status_exerciser_reports_status_and_memory_paths(self):
        report = build_status_exercise()

        self.assertEqual(report["status"]["Probe Profile"], PK4_PROFILE_NAME)
        self.assertEqual(report["status"]["Execution Slot"], "app")
        self.assertEqual(report["memoryExercises"]["bootWrite"]["region"], "boot")
        self.assertEqual(report["memoryExercises"]["appWrite"]["region"], "app")
        self.assertEqual(report["memoryExercises"]["app2Write"]["region"], "app2")
        self.assertEqual(report["memoryExercises"]["relativeAppWrite"]["region"], "app")
        self.assertEqual(report["memoryExercises"]["bootWrite"]["dataHex"], "424f4f54")
        self.assertEqual(report["memoryExercises"]["app2Write"]["dataHex"], "44415021")
        self.assertEqual(report["postExerciseStatus"]["Last Program Region"], "app")
        self.assertEqual(report["postExerciseStatus"]["Last Program Role"], PK4_PRIMARY_ROLE)


if __name__ == "__main__":
    unittest.main()