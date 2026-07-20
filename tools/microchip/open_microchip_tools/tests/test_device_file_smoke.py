import gzip
import tempfile
import unittest
from pathlib import Path

from mchp_ri4.asset_storage import export_yaml_gzip_file
from mchp_ri4.device_file import DeviceFile


_XML = """<?xml version='1.0'?>
<root>
  <version>17.2</version>
  <commit>abc123</commit>
  <processor>PIC16F1509</processor>
  <script>
    <function>Foo</function>
    <scrbytes>
      <byte>0</byte>
      <byte>0x01</byte>
      <byte>255</byte>
      <byte>0x100</byte>
    </scrbytes>
  </script>

  <processor>Other</processor>
  <script>
    <function>Bar</function>
    <scrbytes>
      <byte>0x2</byte>
    </scrbytes>
  </script>
</root>
"""


class TestDeviceFileSmoke(unittest.TestCase):
    def test_parse_filters_processor_and_bytes(self):
        df = DeviceFile.from_xml_text("pic16f1509", _XML)
        self.assertEqual(df.version.strip(), "17.2")
        self.assertEqual(df.commit.strip(), "abc123")
        self.assertEqual(len(df.scripts), 1)

        s = df.get_script("foo")
        self.assertEqual(s.method, "Foo")
        self.assertEqual(s.data, bytes([0, 1, 255, 0]))

    def test_suffix_lookup(self):
        df = DeviceFile.from_xml_text("PIC16F1509", _XML)
        df.set_script_suffix("_SUF")

        # Not present, with suffix not present either.
        self.assertIsNone(df.get_script_basic("Nope"))

        # Add a suffixed script to validate matching.
        df.scripts.append(type(df.scripts[0])(method="Baz_SUF", data=b"\x01"))
        self.assertIsNotNone(df.get_script_basic("Baz"))
        self.assertEqual(df.get_script("Baz").method, "Baz_SUF")

    def test_parse_gzip_xml_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scripts.xml.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(_XML)
            df = DeviceFile.from_xml_path("PIC16F1509", str(path))
            self.assertEqual(df.get_script("Foo").data, bytes([0, 1, 255, 0]))

    def test_parse_exported_yaml_gzip_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "scripts.xml"
            yaml_path = Path(tmp) / "scripts.yaml.gz"
            xml_path.write_text(
                """<?xml version='1.0'?>
<scripts>
  <version>1</version>
  <commit>abc</commit>
  <script>
    <function>Foo</function>
    <processor>PIC16F1509</processor>
    <scrbytes><byte>0x01</byte><byte>0x02</byte></scrbytes>
  </script>
  <script>
    <function>Bar</function>
    <processor>Other</processor>
    <scrbytes><byte>0xFF</byte></scrbytes>
  </script>
</scripts>
""",
                encoding="utf-8",
            )
            export_yaml_gzip_file(xml_path, yaml_path)

            df = DeviceFile.from_xml_path("PIC16F1509", str(yaml_path))

            self.assertEqual(df.version, "1")
            self.assertEqual(df.commit, "abc")
            self.assertEqual(df.get_script("Foo").data, bytes([1, 2]))
            self.assertIsNone(df.get_script_basic("Bar"))

    def test_legacy_import_and_java_method_names(self):
        from com.microchip.mplab.libs.RI4ToolsController.scriptcode.implementations.DeviceFileSAXReader import (
            DeviceFileSAXReader,
        )
        from com.microchip.mplab.libs.RI4ToolsController.scriptcode.interfaces.Script import Script

        df = DeviceFileSAXReader("PIC16F1509", _XML)
        scripts = df.getScripts()
        self.assertEqual(len(scripts), 1)

        s = scripts[0]
        self.assertIsInstance(s, Script)
        self.assertEqual(s.getMethod(), "Foo")
        self.assertEqual(s.getData(), bytes([0, 1, 255, 0]))
        self.assertEqual(
            s.addParams(1),
            b"\x04\x00\x00\x00" + b"\x04\x00\x00\x00" + b"\x01\x00\x00\x00" + s.getData(),
        )


if __name__ == "__main__":
    unittest.main()
