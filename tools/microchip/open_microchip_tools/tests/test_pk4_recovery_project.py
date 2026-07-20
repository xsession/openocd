import unittest

from zephyr_pickit4_replacement.pk4_recovery_project import build_pk4_recovery_project, exercise_pk4_recovery_project


class TestPk4RecoveryProject(unittest.TestCase):
    def test_build_recovery_project_exposes_boot_primary_and_secondary_slots(self):
        project = build_pk4_recovery_project()

        self.assertEqual(project.name, "pk4_cleanroom_recovery_project")
        self.assertEqual(project.boot.name, "boot")
        self.assertEqual(project.primary_app.name, "app")
        self.assertEqual(project.secondary_app.name, "app2")
        self.assertEqual(project.primary_app.role, "RI4 host-facing app slot")
        self.assertEqual(project.secondary_app.role, "CMSIS-DAP control/update slot")

    def test_recovery_project_exercise_roundtrips_primary_and_secondary_slots(self):
        report = exercise_pk4_recovery_project()

        self.assertEqual(report["project"]["name"], "pk4_cleanroom_recovery_project")
        self.assertEqual(report["writes"]["primary"]["script"], "WritePrimarySlot")
        self.assertEqual(report["writes"]["secondary"]["script"], "WriteSecondarySlot")
        self.assertEqual(report["reads"]["primary"]["dataHex"], "41505021")
        self.assertEqual(report["reads"]["secondary"]["dataHex"], "44415021")
        self.assertEqual(report["status"]["lastProgramRegion"], "app2")
        self.assertEqual(report["status"]["lastProgramRole"], "CMSIS-DAP control/update slot")


if __name__ == "__main__":
    unittest.main()