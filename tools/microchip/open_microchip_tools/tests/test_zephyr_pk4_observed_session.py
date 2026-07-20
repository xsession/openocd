import unittest

from zephyr_pickit4_replacement.pk4_observed_profile import PK4_APP2_BASE
from zephyr_pickit4_replacement.pk4_observed_session import create_pk4_observed_session


class TestZephyrPk4ObservedSession(unittest.TestCase):
    def test_status_keys_roundtrip_over_ri4_host_stack(self):
        session, _probe = create_pk4_observed_session()

        self.assertEqual(session.get_status_value("Primary Role"), "RI4 host-facing app slot")
        self.assertEqual(session.get_status_value("Secondary Role"), "CMSIS-DAP control/update slot")
        self.assertEqual(session.get_status_value("Execution Slot"), "app")

        session.set_pc(PK4_APP2_BASE + 0x120)

        self.assertEqual(session.get_status_value("Execution Slot"), "app2")
        self.assertEqual(session.get_status_value("Execution Role"), "CMSIS-DAP control/update slot")

    def test_primary_and_secondary_slot_helpers_target_expected_regions(self):
        session, probe = create_pk4_observed_session()

        primary_write = session.write_primary_slot(0x20, b"APP!")
        secondary_write = session.write_secondary_slot(0x10, b"DAP!")
        primary_read = session.read_primary_slot(0x20, 4)
        secondary_read = session.read_secondary_slot(0x10, 4)

        self.assertEqual(primary_write["script"], "WritePrimarySlot")
        self.assertEqual(secondary_write["script"], "WriteSecondarySlot")
        self.assertEqual(primary_read["script"], "ReadPrimarySlot")
        self.assertEqual(secondary_read["script"], "ReadSecondarySlot")
        self.assertEqual(primary_read["dataHex"], "41505021")
        self.assertEqual(secondary_read["dataHex"], "44415021")
        self.assertEqual(bytes(probe.model.app_flash[0x20:0x24]), b"APP!")
        self.assertEqual(bytes(probe.model.app2_flash[0x10:0x14]), b"DAP!")
        self.assertEqual(session.get_status_value("Last Program Region"), "app2")
        self.assertEqual(session.get_status_value("Last Program Role"), "CMSIS-DAP control/update slot")

    def test_secondary_slot_helper_can_be_followed_by_explicit_readback(self):
        session, probe = create_pk4_observed_session()

        session.write_secondary_slot(0x40, b"CMSI")
        data = session.read_secondary_slot(0x40, 4)

        self.assertEqual(data["address"], PK4_APP2_BASE + 0x40)
        self.assertEqual(data["script"], "ReadSecondarySlot")
        self.assertEqual(data["dataHex"], "434d5349")
        self.assertEqual(bytes(probe.model.app2_flash[0x40:0x44]), b"CMSI")


if __name__ == "__main__":
    unittest.main()