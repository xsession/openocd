from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from .util import local_name


def _find_named(parent: ET.Element, node_type: str, name: str) -> list[ET.Element]:
    result: list[ET.Element] = []
    for element in parent.iter():
        if local_name(element.tag) != node_type:
            continue
        for child in element:
            if local_name(child.tag) == "name" and (child.text or "") == name:
                result.append(element)
                break
    return result


def apply_patch(svd_path: Path, patch_path: Path) -> None:
    if not patch_path.exists():
        return
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    tree = ET.parse(svd_path)
    root = tree.getroot()
    for old, new in patch.get("rename_peripherals", {}).items():
        for peripheral in _find_named(root, "peripheral", old):
            for child in peripheral:
                if local_name(child.tag) == "name":
                    child.text = new
    for peripheral_name in patch.get("delete_peripherals", []):
        peripherals = next((e for e in root.iter() if local_name(e.tag) == "peripherals"), None)
        if peripherals is not None:
            for peripheral in list(peripherals):
                names = [c.text for c in peripheral if local_name(c.tag) == "name"]
                if peripheral_name in names:
                    peripherals.remove(peripheral)
    tree.write(svd_path, encoding="utf-8", xml_declaration=True)
