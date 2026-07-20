import unittest

from zephyr_pickit4_replacement.demo import run_pk4_observed_demo, run_stub_demo


class TestZephyrDemo(unittest.TestCase):
    def test_stub_demo_returns_readback_and_status(self):
        report = run_stub_demo(family="PIC18", processor="PIC18F_STUB", write_address=0x14, write_data=b"\xAA\xBB")

        self.assertEqual(report["family"], "PIC18")
        self.assertEqual(report["readBack"]["dataHex"], "aabb")
        self.assertEqual(report["status"]["Family"], "PIC18")

    def test_pk4_observed_demo_surfaces_primary_and_secondary_slots(self):
        report = run_pk4_observed_demo()

        self.assertEqual(report["status"]["Probe Profile"], "PK4_OBSERVED_DUAL_APP_LAYOUT")
        self.assertEqual(report["primaryReadBack"]["dataHex"], "41505021")
        self.assertEqual(report["secondaryReadBack"]["dataHex"], "44415021")
        self.assertEqual(report["status"]["Last Program Region"], "app2")
        self.assertEqual(report["status"]["Last Program Role"], "CMSIS-DAP control/update slot")


if __name__ == "__main__":
    unittest.main()