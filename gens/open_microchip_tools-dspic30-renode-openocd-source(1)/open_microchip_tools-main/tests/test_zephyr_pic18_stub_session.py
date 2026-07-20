import tempfile
import unittest
from pathlib import Path

from zephyr_pickit4_replacement.pic18_stub_session import create_pic18_stub_session, create_stub_family_session


class TestZephyrPic18StubSession(unittest.TestCase):
    def test_pic18_stub_scripts_drive_named_session(self):
        session, probe = create_pic18_stub_session("PIC18F_STUB")

        session.enter_debug_mode()
        session.set_pc(0x12345678)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x12345678)

        session.erase_chip()
        session.write_program(0x10, b"\x01\x02\x03\x04")
        read_back = session.read_program(0x10, 4)
        self.assertEqual(read_back["dataHex"], "01020304")
        self.assertEqual(probe.get_status_value("Debug Mode"), "1")
        self.assertEqual(probe.get_status_value("Target Halted"), "1")

    def test_pic18_stub_scripts_support_program_hex_verify(self):
        session, probe = create_pic18_stub_session("PIC18F_STUB")

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "stub.hex"
            hex_path.write_text(":0400100001020304E2\n:00000001FF\n", encoding="utf-8")
            result = session.program_hex(str(hex_path), erase_first=True, verify=True)

        self.assertEqual(result["segmentCount"], 1)
        self.assertEqual(result["segments"][0]["address"], 0x10)
        self.assertEqual(bytes(probe.flash[0x10:0x14]), b"\x01\x02\x03\x04")

    def test_pic18_stub_can_dump_then_write_back_hex(self):
        session, probe = create_pic18_stub_session("PIC18F_STUB")
        probe.flash[0x30:0x34] = b"\xDE\xAD\xBE\xEF"

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "roundtrip.hex"
            dump_result = session.dump_program_hex(str(hex_path), start_address=0x30, length=4, chunk_size=4)
            self.assertEqual(dump_result["segmentCount"], 1)

            probe.flash[0x30:0x34] = b"\xFF\xFF\xFF\xFF"
            result = session.program_hex(str(hex_path), erase_first=False, verify=True)

        self.assertEqual(result["segmentCount"], 1)
        self.assertEqual(bytes(probe.flash[0x30:0x34]), b"\xDE\xAD\xBE\xEF")

    def test_pic18_stub_probe_reports_status_keys(self):
        session, probe = create_pic18_stub_session("PIC18F_STUB")
        session.enter_debug_mode()
        session.set_pc(0x40)
        self.assertEqual(probe.get_status_value("Commands in progress"), "0")
        self.assertEqual(probe.get_status_value("Debug Mode"), "1")
        self.assertEqual(probe.get_status_value("Target Halted"), "1")
        self.assertEqual(probe.get_status_value("Program Counter"), "0x00000040")

    def test_pic16_enhanced_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("PIC16Enhanced", "PIC16F1509_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.set_pc(0x50)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x50)

        session.erase_chip()
        session.write_program(0x24, b"\x99\x88\x77\x66")
        read_back = session.read_program(0x24, 4)
        self.assertEqual(read_back["dataHex"], "99887766")
        self.assertEqual(probe.get_status_value("Family"), "PIC16ENHANCED")

    def test_arm_mpu_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("ARM_MPU", "ATSAME70_STUB")

        session.enter_debug_mode()
        session.set_pc(0x20001000)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x20001000)

        session.write_program(0x20, b"\xAA\xBB\xCC\xDD")
        read_back = session.read_program(0x20, 4)
        self.assertEqual(read_back["dataHex"], "aabbccdd")
        self.assertEqual(probe.get_status_value("Family"), "ARM_MPU")

    def test_pic32mz_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("PIC32MZ", "PIC32MZ2048EFH_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.set_pc(0x9D000000)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x9D000000)

        session.erase_chip()
        session.write_program(0x40, b"\xDE\xAD\xBE\xEF")
        read_back = session.read_program(0x40, 4)
        self.assertEqual(read_back["dataHex"], "deadbeef")
        self.assertEqual(probe.get_status_value("Family"), "PIC32MZ")

    def test_dspic33a_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("DSPIC33A", "DSPIC33AK128MC106_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.set_pc(0x000120)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x000120)

        session.erase_chip()
        session.write_program(0x60, b"\x11\x22\x33\x44")
        read_back = session.read_program(0x60, 4)
        self.assertEqual(read_back["dataHex"], "11223344")
        self.assertEqual(probe.get_status_value("Family"), "DSPIC33A")

    def test_dspic30f_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("DSPIC30F", "DSPIC30F5011_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.enter_debug_mode()
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0)

        session.erase_chip()
        session.write_program(0x28, b"\x10\x20\x30\x40")
        read_back = session.read_program(0x28, 4)
        self.assertEqual(read_back["dataHex"], "10203040")
        self.assertEqual(probe.get_status_value("Family"), "DSPIC30F")

    def test_dspic33fj_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("DSPIC33FJ", "DSPIC33FJ256GP710A_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.enter_debug_mode()
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0)

        session.erase_chip()
        session.write_program(0x2C, b"\x44\x33\x22\x11")
        read_back = session.read_program(0x2C, 4)
        self.assertEqual(read_back["dataHex"], "44332211")
        self.assertEqual(probe.get_status_value("Family"), "DSPIC33FJ")

    def test_dspic33ep_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("DSPIC33EP", "DSPIC33EP512MU810_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.set_pc(0x140)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x140)

        session.erase_chip()
        session.write_program(0x30, b"\xCA\xFE\xBA\xBE")
        read_back = session.read_program(0x30, 4)
        self.assertEqual(read_back["dataHex"], "cafebabe")
        self.assertEqual(probe.get_status_value("Family"), "DSPIC33EP")

    def test_avr_stub_scripts_drive_named_session(self):
        session, probe = create_stub_family_session("AVR", "ATMEGA4809_STUB")

        program_entry = session.enter_programming_mode()
        self.assertIsNotNone(program_entry)
        session.enter_debug_mode()
        session.set_pc(0x80)
        pc = session.get_pc()
        self.assertEqual(pc["pc"], 0x80)

        session.erase_chip()
        session.write_program(0x20, b"\x55\x66\x77\x88")
        read_back = session.read_program(0x20, 4)
        self.assertEqual(read_back["dataHex"], "55667788")
        self.assertEqual(probe.get_status_value("Family"), "AVR")


if __name__ == "__main__":
    unittest.main()