from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
extension = root / "extension"
metadata = json.loads((extension / "package.json").read_text(encoding="utf-8"))
version = metadata["version"]
output = extension / f"c2000-debug-{version}.vsix"

with tempfile.TemporaryDirectory() as temp_dir:
    stage = Path(temp_dir)
    payload = stage / "extension"
    payload.mkdir()

    for name in ["package.json", "README.md"]:
        shutil.copy2(extension / name, payload / name)
    shutil.copy2(root / "LICENSE", payload / "LICENSE")
    shutil.copytree(extension / "dist", payload / "dist")
    shutil.copytree(root / "bridge", payload / "bridge")

    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{metadata['name']}" Version="{version}" Publisher="{metadata['publisher']}" />
    <DisplayName>{metadata['displayName']}</DisplayName>
    <Description xml:space="preserve">{metadata['description']}</Description>
    <Tags>{','.join(metadata.get('keywords', []))}</Tags>
    <Categories>Debuggers</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{metadata['engines']['vscode']}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
'''
    (stage / "extension.vsixmanifest").write_text(manifest, encoding="utf-8")
    content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="map" ContentType="application/json" />
  <Default Extension="md" ContentType="text/markdown" />
  <Default Extension="txt" ContentType="text/plain" />
  <Default Extension="xml" ContentType="text/xml" />
  <Default Extension="ps1" ContentType="text/plain" />
  <Default Extension="sh" ContentType="text/plain" />
  <Default Extension="vsixmanifest" ContentType="text/xml" />
</Types>
'''
    (stage / "[Content_Types].xml").write_text(content_types, encoding="utf-8")

    output.unlink(missing_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in sorted(stage.rglob("*")):
            if item.is_file():
                archive.write(item, item.relative_to(stage).as_posix())

print(output)
