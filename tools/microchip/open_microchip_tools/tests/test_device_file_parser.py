import unittest

from mchp_ri4.device_file import DeviceFile


class TestDeviceFileParser(unittest.TestCase):
    def test_parses_nested_processor_layout(self):
        xml_text = """
<scripts>
  <commit>abc123</commit>
  <version>000001</version>
  <script>
    <function>EnterTMOD_LV</function>
    <processor>dsPIC30F5011</processor>
    <scrbytes>
      <byte>0xAA</byte>
      <byte>0xBB</byte>
    </scrbytes>
  </script>
  <script>
    <function>OtherProcScript</function>
    <processor>OtherPart</processor>
    <scrbytes>
      <byte>0xCC</byte>
    </scrbytes>
  </script>
</scripts>
"""
        device_file = DeviceFile.from_xml_text("dsPIC30F5011", xml_text)
        names = [script.method for script in device_file.getScripts()]
        self.assertEqual(names, ["EnterTMOD_LV"])
        self.assertEqual(device_file.getScript("EnterTMOD_LV").getData(), bytes((0xAA, 0xBB)))


if __name__ == "__main__":
    unittest.main()