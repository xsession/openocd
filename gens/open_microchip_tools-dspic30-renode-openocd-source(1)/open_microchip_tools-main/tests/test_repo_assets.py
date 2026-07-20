import json
import tempfile
import unittest
import gzip
from pathlib import Path

from mchp_ri4.repo_assets import (
    collect_repo_assets,
    collect_supported_family_packs,
    resolve_repo_device_file,
    resolve_repo_scripts_path,
    supported_processors_from_device_support,
)


class TestRepoAssets(unittest.TestCase):
    def test_supported_processors_from_device_support_accepts_yes_beta_alpha(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "device_support.xml"
            path.write_text(
                """<?xml version='1.0'?>
<mp:deviceSupport xmlns:mp='http://crownking/mplab'>
  <mp:family mp:family='16x'>
    <mp:device mp:name='PIC16F_A'><mp:support mp:pk4d='yes' mp:pk4p='no'/></mp:device>
    <mp:device mp:name='PIC16F_B'><mp:support mp:pk4d='no' mp:pk4p='beta'/></mp:device>
    <mp:device mp:name='PIC16F_C'><mp:support mp:pk4d='no' mp:pk4p='alpha'/></mp:device>
    <mp:device mp:name='PIC16F_D'><mp:support mp:pk4d='no' mp:pk4p='no'/></mp:device>
  </mp:family>
</mp:deviceSupport>
""",
                encoding="utf-8",
            )
            self.assertEqual(
                supported_processors_from_device_support(path, "pk4"),
                {"PIC16F_A", "PIC16F_B", "PIC16F_C"},
            )

        def test_supported_processors_from_device_support_accepts_gzip_xml(self):
                with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / "device_support.xml.gz"
                        with gzip.open(path, "wt", encoding="utf-8") as handle:
                                handle.write(
                                        """<?xml version='1.0'?>
<mp:deviceSupport xmlns:mp='http://crownking/mplab'>
    <mp:family mp:family='16x'>
        <mp:device mp:name='PIC16F_A'><mp:support mp:pk4d='yes'/></mp:device>
    </mp:family>
</mp:deviceSupport>
"""
                                )
                        self.assertEqual(supported_processors_from_device_support(path, "pk4"), {"PIC16F_A"})

    def test_collect_repo_assets_copies_toolpack_and_device_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mplab = root / "mplab"
            tool_dir = mplab / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541"
            (tool_dir / "firmware" / "ptg").mkdir(parents=True)
            (tool_dir / "firmware" / "app.hex").write_text(":00000001FF\n", encoding="utf-8")
            (tool_dir / "firmware" / "boot.hex").write_text(":00000001FF\n", encoding="utf-8")
            (tool_dir / "firmware" / "scripts.xml").write_text("<scripts />", encoding="utf-8")
            (tool_dir / "firmware" / "scripts-v2.zip").write_bytes(b"ZIP")
            (tool_dir / "firmware" / "PK4FW_001000.jam").write_text("jam", encoding="utf-8")
            (tool_dir / "firmware" / "ptg" / "ToolInfo").write_text("info", encoding="utf-8")
            (tool_dir / "firmware" / "Pk4HybridTooImpl.toolMediator").write_text("mediator", encoding="utf-8")
            (tool_dir / "device_support.xml").write_text("<device-support />", encoding="utf-8")
            (tool_dir / "pickit4.xml").write_text("<pickit4 />", encoding="utf-8")
            (tool_dir / "Microchip.PICkit4_TP.pdsc").write_text("pdsc", encoding="utf-8")

            device_dir = mplab / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.5.254"
            (device_dir / "edc").mkdir(parents=True)
            (device_dir / "edc" / "dsPIC30F5011.PIC").write_text("PIC", encoding="utf-8")
            (device_dir / "Microchip.dsPIC30F_DFP.pdsc").write_text("pdsc", encoding="utf-8")
            (device_dir / "Microchip.dsPIC30F_DFP.sha1").write_text("sha1", encoding="utf-8")

            vendor = root / "vendor"
            result = collect_repo_assets(
                mplab_root=mplab,
                tool="pk4",
                processor="dsPIC30F5011",
                destination_root=vendor,
            )

            self.assertTrue((vendor / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "firmware" / "scripts.xml.gz").exists())
            self.assertFalse((vendor / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "firmware" / "scripts.xml").exists())
            self.assertTrue((vendor / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "firmware" / "app.hex").exists())
            self.assertTrue((vendor / "tool_firmware" / "pk4" / "app.hex").exists())
            self.assertTrue((vendor / "tool_firmware" / "pk4" / "boot.hex").exists())
            self.assertTrue((vendor / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.5.254" / "edc" / "dsPIC30F5011.PIC.gz").exists())
            self.assertEqual(result.tool, "PK4")
            manifest = json.loads((vendor / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["toolpacks"]["PK4"]["pack"], "PICkit4_TP")
            self.assertTrue(manifest["toolpacks"]["PK4"]["scriptsPath"].endswith("scripts.xml.gz"))
            self.assertTrue(manifest["toolpacks"]["PK4"]["firmwarePath"].endswith("PK4FW_001000.jam"))
            self.assertEqual(manifest["devicePacks"]["dsPIC30F5011"]["pack"], "dsPIC30F_DFP")
            self.assertTrue(manifest["devicePacks"]["dsPIC30F5011"]["deviceFilePath"].endswith(".PIC.gz"))

    def test_resolve_repo_scripts_path_prefers_latest_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            packs = Path(tmp) / "PICkit4_TP"
            (packs / "2.11.0" / "firmware").mkdir(parents=True)
            (packs / "2.12.2541" / "firmware").mkdir(parents=True)
            (packs / "2.11.0" / "firmware" / "scripts.xml").write_text("old", encoding="utf-8")
            latest = packs / "2.12.2541" / "firmware" / "scripts.xml.gz"
            with gzip.open(latest, "wt", encoding="utf-8") as handle:
                handle.write("new")
            self.assertEqual(resolve_repo_scripts_path("pk4", base=Path(tmp)), latest)

    def test_resolve_repo_scripts_path_falls_back_to_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            packs = Path(tmp) / "PICkit4_TP" / "2.12.2541" / "firmware"
            packs.mkdir(parents=True)
            latest = packs / "scripts.yaml.gz"
            with gzip.open(latest, "wt", encoding="utf-8") as handle:
                handle.write("document:\n  scripts: {}\n")
            self.assertEqual(resolve_repo_scripts_path("pk4", base=Path(tmp)), latest)

    def test_resolve_repo_device_file_prefers_compressed_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            packs = Path(tmp) / "dsPIC30F_DFP" / "1.5.254" / "edc"
            packs.mkdir(parents=True)
            path = packs / "dsPIC30F5011.PIC.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write("PIC")
            self.assertEqual(resolve_repo_device_file("dsPIC30F5011", base=Path(tmp)), path)

    def test_collect_supported_family_packs_copies_unique_supported_dfps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mplab = root / "mplab"

            pk4_dir = mplab / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541"
            (pk4_dir / "firmware").mkdir(parents=True)
            (pk4_dir / "firmware" / "app.hex").write_text(":00000001FF\n", encoding="utf-8")
            (pk4_dir / "firmware" / "boot.hex").write_text(":00000001FF\n", encoding="utf-8")
            (pk4_dir / "firmware" / "scripts.xml").write_text("<scripts />", encoding="utf-8")
            (pk4_dir / "firmware" / "PK4FW_001000.jam").write_text("jam", encoding="utf-8")
            (pk4_dir / "device_support.xml").write_text(
                """<?xml version='1.0'?>
<mp:deviceSupport xmlns:mp='http://crownking/mplab'>
    <mp:family mp:family='16x'>
        <mp:device mp:name='PIC16F_A'><mp:support mp:pk4p='yes'/></mp:device>
    </mp:family>
</mp:deviceSupport>
""",
                encoding="utf-8",
            )
            (pk4_dir / "Microchip.PICkit4_TP.pdsc").write_text("pdsc", encoding="utf-8")

            icd4_dir = mplab / "packs" / "Microchip" / "ICD4_TP" / "2.12.2362"
            (icd4_dir / "firmware").mkdir(parents=True)
            (icd4_dir / "firmware" / "app.hex").write_text(":00000001FF\n", encoding="utf-8")
            (icd4_dir / "firmware" / "boot.hex").write_text(":00000001FF\n", encoding="utf-8")
            (icd4_dir / "firmware" / "scripts.xml").write_text("<scripts />", encoding="utf-8")
            (icd4_dir / "firmware" / "ICD4FW_001000.jam").write_text("jam", encoding="utf-8")
            (icd4_dir / "device_support.xml").write_text(
                """<?xml version='1.0'?>
<mp:deviceSupport xmlns:mp='http://crownking/mplab'>
    <mp:family mp:family='30F'>
        <mp:device mp:name='DSPIC30F_X'><mp:support mp:icd4p='yes'/></mp:device>
    </mp:family>
</mp:deviceSupport>
""",
                encoding="utf-8",
            )
            (icd4_dir / "Microchip.ICD4_TP.pdsc").write_text("pdsc", encoding="utf-8")

            pic16_dir = mplab / "packs" / "Microchip" / "PIC16Fxxx_DFP" / "1.0.0"
            (pic16_dir / "edc").mkdir(parents=True)
            (pic16_dir / "edc" / "PIC16F_A.PIC").write_text("PIC16", encoding="utf-8")
            (pic16_dir / "edc" / "PIC16F_B.PIC").write_text("PIC16B", encoding="utf-8")
            (pic16_dir / "Microchip.PIC16Fxxx_DFP.pdsc").write_text("pdsc", encoding="utf-8")

            dspic_dir = mplab / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.0.0"
            (dspic_dir / "edc").mkdir(parents=True)
            (dspic_dir / "edc" / "DSPIC30F_X.PIC").write_text("DSPIC", encoding="utf-8")
            (dspic_dir / "Microchip.dsPIC30F_DFP.pdsc").write_text("pdsc", encoding="utf-8")

            vendor = root / "vendor"
            result = collect_supported_family_packs(mplab_root=mplab, tools=("pk4", "icd4"), destination_root=vendor)

            self.assertEqual(result["toolpackCount"], 2)
            self.assertEqual(result["familyPackCount"], 2)
            self.assertTrue((vendor / "packs" / "Microchip" / "PICkit4_TP" / "2.12.2541" / "firmware" / "scripts.xml.gz").exists())
            self.assertTrue((vendor / "packs" / "Microchip" / "ICD4_TP" / "2.12.2362" / "firmware" / "scripts.xml.gz").exists())
            self.assertTrue((vendor / "packs" / "Microchip" / "PIC16Fxxx_DFP" / "1.0.0" / "edc" / "PIC16F_A.PIC.gz").exists())
            self.assertTrue((vendor / "packs" / "Microchip" / "dsPIC30F_DFP" / "1.0.0" / "edc" / "DSPIC30F_X.PIC.gz").exists())
            manifest = json.loads((vendor / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("PIC16Fxxx_DFP@1.0.0", manifest["familyPacks"])
            self.assertIn("dsPIC30F_DFP@1.0.0", manifest["familyPacks"])
            self.assertTrue(manifest["toolpacks"]["PK4"]["scriptsPath"].endswith("scripts.xml.gz"))
            self.assertTrue(manifest["toolpacks"]["ICD4"]["scriptsPath"].endswith("scripts.xml.gz"))
            self.assertEqual(len(manifest["firmwarePackages"]), 2)


if __name__ == "__main__":
    unittest.main()