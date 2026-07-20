import tempfile
import unittest
from pathlib import Path

from mchp_simulator.firmware_image import FirmwareImage, Segment


class TestFirmwareImageHexExport(unittest.TestCase):
    def test_round_trips_via_intel_hex_text(self):
        image = FirmwareImage(
            segments=(
                Segment(address=0x120, data=b"\x01\x02\x03\x04"),
                Segment(address=0x10020, data=b"\xAA\xBB"),
            )
        )

        text = image.to_intel_hex_text(bytes_per_record=4)
        rebuilt = FirmwareImage.from_intel_hex_text(text)

        self.assertEqual(rebuilt.to_byte_dict(), image.to_byte_dict())

    def test_writes_hex_file(self):
        image = FirmwareImage(segments=(Segment(address=0x20, data=b"\x10\x20\x30\x40"),))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dump.hex"
            image.to_intel_hex_path(str(path))
            self.assertTrue(path.exists())
            parsed = FirmwareImage.from_intel_hex_path(str(path))
        self.assertEqual(parsed.to_byte_dict(), image.to_byte_dict())


if __name__ == "__main__":
    unittest.main()