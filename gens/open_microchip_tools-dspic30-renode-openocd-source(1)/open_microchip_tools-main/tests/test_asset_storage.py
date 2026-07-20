import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from mchp_ri4.asset_storage import build_storage_report, create_tar_xz_archive, export_yaml_tree, read_yaml_lines


class TestAssetStorage(unittest.TestCase):
    def test_export_yaml_tree_reads_gzip_xmlish_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "vendor"
            output = root / "yaml"
            xml_path = source / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "pickit4.xml.gz"
            pic_path = source / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.5.254" / "edc" / "dsPIC30F5011.PIC.gz"
            xml_path.parent.mkdir(parents=True)
            pic_path.parent.mkdir(parents=True)

            import gzip

            with gzip.open(xml_path, "wt", encoding="utf-8") as handle:
                handle.write("<tool version='1'><name>PICkit4</name></tool>")
            with gzip.open(pic_path, "wt", encoding="utf-8") as handle:
                handle.write("<device id='1'><name>dsPIC30F5011</name></device>")

            result = export_yaml_tree(source, output)

            self.assertEqual(result["exportedCount"], 2)
            pickit_yaml = output / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "pickit4.yaml"
            device_yaml = output / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.5.254" / "edc" / "dsPIC30F5011.yaml"
            self.assertTrue(pickit_yaml.exists())
            self.assertTrue(device_yaml.exists())
            self.assertIn("tool:", pickit_yaml.read_text(encoding="utf-8"))
            self.assertIn("attributes:", pickit_yaml.read_text(encoding="utf-8"))
            self.assertIn("device:", device_yaml.read_text(encoding="utf-8"))

    def test_export_yaml_tree_can_write_gzip_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "vendor"
            output = root / "yaml"
            xml_path = source / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "pickit4.xml.gz"
            xml_path.parent.mkdir(parents=True)

            import gzip

            with gzip.open(xml_path, "wt", encoding="utf-8") as handle:
                handle.write("<tool xmlns:edc='http://crownking/edc'><edc:name>PICkit4</edc:name></tool>")

            result = export_yaml_tree(source, output, gzip_output=True)

            self.assertTrue(result["gzipOutput"])
            pickit_yaml = output / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "pickit4.yaml.gz"
            self.assertTrue(pickit_yaml.exists())
            with gzip.open(pickit_yaml, "rt", encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("namespaces:", content)
            self.assertIn("edc:", content)
            self.assertIn("document:", content)

    def test_create_tar_xz_archive_wraps_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "vendor" / "mplabx"
            archive = root / "archives" / "mplabx.tar.xz"
            payload = source / "asset_manifest.json"
            payload.parent.mkdir(parents=True)
            payload.write_text("{}\n", encoding="utf-8")

            result = create_tar_xz_archive(source, archive)

            self.assertEqual(result["archivePath"], str(archive))
            self.assertTrue(archive.exists())
            with tarfile.open(archive, "r:xz") as handle:
                names = handle.getnames()
            self.assertIn("mplabx/asset_manifest.json", names)

    def test_read_yaml_lines_reads_gzip_yaml_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "sample.yaml.gz"
            import gzip

            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write("one\ntwo\nthree\nfour\n")

            result = read_yaml_lines(path, start_line=2, end_line=3)

            self.assertEqual(result["lineCount"], 2)
            self.assertEqual(result["startLine"], 2)
            self.assertEqual(result["endLine"], 3)
            self.assertEqual(result["text"], "two\nthree")

    def test_build_storage_report_counts_raw_and_compressed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml_path = root / "pickit4.xml.gz"
            raw_path = root / "notes.xml"
            import gzip

            with gzip.open(xml_path, "wt", encoding="utf-8") as handle:
                handle.write("<tool />")
            raw_path.write_text("<tool />", encoding="utf-8")

            report = build_storage_report(root)

            self.assertEqual(report["xmlishFileCount"], 2)
            self.assertEqual(report["rawXmlishCount"], 1)
            self.assertEqual(report["compressedXmlishCount"], 1)
            self.assertEqual(report["duplicateCompressedGroupCount"], 0)


if __name__ == "__main__":
    unittest.main()