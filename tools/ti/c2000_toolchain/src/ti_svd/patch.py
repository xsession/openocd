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


def _child_text(parent: ET.Element, child_name: str) -> str:
    child_name = child_name.lower()
    for child in parent:
        if local_name(child.tag) == child_name:
            return child.text or ""
    return ""


def _same_address(left: str, right: str) -> bool:
    try:
        return int(left, 0) == int(right, 0)
    except ValueError:
        return left.lower() == right.lower()


def _peripherals_root(root: ET.Element) -> ET.Element | None:
    return next((e for e in root.iter() if local_name(e.tag) == "peripherals"), None)


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
        peripherals = _peripherals_root(root)
        if peripherals is not None:
            for peripheral in list(peripherals):
                names = [c.text for c in peripheral if local_name(c.tag) == "name"]
                if peripheral_name in names:
                    peripherals.remove(peripheral)
    for delete in patch.get("delete_peripherals_by_address", []):
        peripherals = _peripherals_root(root)
        if peripherals is None:
            continue
        name = delete["name"]
        base_address = delete["baseAddress"]
        for peripheral in list(peripherals):
            if _child_text(peripheral, "name") != name:
                continue
            if _same_address(_child_text(peripheral, "baseAddress"), base_address):
                peripherals.remove(peripheral)
    tree.write(svd_path, encoding="utf-8", xml_declaration=True)
