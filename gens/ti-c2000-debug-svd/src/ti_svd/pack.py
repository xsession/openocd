from __future__ import annotations

import json
import shutil
import tempfile
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .config import repository_root
from .models import DeviceManifest
from .util import indent_xml, local_name


def _lock_entry(device_id: str, root: Path) -> dict:
    data = json.loads((root / "sources.lock.json").read_text(encoding="utf-8"))
    return data[device_id]


def fetch_pack(device_id: str, root: Path | None = None, cache_dir: Path | None = None) -> Path:
    root = root or repository_root()
    entry = _lock_entry(device_id, root)
    cache_dir = cache_dir or root / "sources" / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / Path(entry["url"]).name
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    request = urllib.request.Request(entry["url"], headers={"User-Agent": "ti-c2000-mspm0-svd/0.2"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def extract_svd_from_pack(pack_path: Path, member_name: str, destination: Path) -> Path:
    with ZipFile(pack_path) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name.lower() == member_name.lower()]
        if not candidates:
            svds = [name for name in archive.namelist() if name.lower().endswith(".svd")]
            raise FileNotFoundError(f"{member_name} not found in {pack_path}; available SVDs: {svds}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(candidates[0]) as source, destination.open("wb") as output:
            shutil.copyfileobj(source, output)
    return destination


def specialize_family_svd(source: Path, destination: Path, manifest: DeviceManifest) -> Path:
    tree = ET.parse(source)
    root = tree.getroot()
    for child in root:
        tag = local_name(child.tag)
        if tag == "name":
            child.text = manifest.name
        elif tag == "description":
            child.text = f"{manifest.name} device view derived from the TI {manifest.family} CMSIS pack."
    # Preserve the vendor XML and only rewrite device-level identity.
    destination.parent.mkdir(parents=True, exist_ok=True)
    indent_xml(root)
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    return destination


def generate_mspm0(manifest: DeviceManifest, root: Path | None = None, offline_pack: Path | None = None) -> Path:
    root = root or repository_root()
    entry = _lock_entry(manifest.id, root)
    pack_path = offline_pack or fetch_pack(manifest.id, root)
    with tempfile.TemporaryDirectory(prefix="ti-svd-") as tmp:
        family_svd = Path(tmp) / entry["svd_member"]
        extract_svd_from_pack(pack_path, entry["svd_member"], family_svd)
        return specialize_family_svd(family_svd, manifest.output, manifest)
