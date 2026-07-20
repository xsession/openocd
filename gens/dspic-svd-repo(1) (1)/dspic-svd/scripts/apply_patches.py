#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd.cortex_debug import validate_cortex_debug_file  # noqa: E402
from dspic_svd.validate import validate_file  # noqa: E402


def text_child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in parent if c.tag.rsplit("}", 1)[-1] == name), None)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def patch_file(config_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    device = config.get("device", config_path.stem)
    svd_path = ROOT / "svd" / f"{device.lower()}.svd"
    if not svd_path.exists():
        return

    tree = ET.parse(svd_path)
    root = tree.getroot()
    registers: dict[str, ET.Element] = {}
    for register in (n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "register"):
        name_node = text_child(register, "name")
        if name_node is not None and name_node.text:
            registers[name_node.text] = register

    changed = False
    for old, new in (config.get("rename_registers") or {}).items():
        register = registers.pop(old, None)
        if register is None:
            continue
        name_node = text_child(register, "name")
        if name_node is not None and name_node.text != new:
            name_node.text = new
            changed = True
        registers[new] = register

    for reg_name, changes in (config.get("registers") or {}).items():
        register = registers.get(reg_name)
        if register is None:
            continue
        for key in ("description", "access", "resetValue", "resetMask"):
            if key not in changes:
                continue
            value = str(changes[key])
            node = text_child(register, key)
            if node is None:
                node = ET.SubElement(register, key)
                node.text = value
                changed = True
            elif node.text != value:
                node.text = value
                changed = True

    if changed:
        ET.indent(root, space="  ")
        tree.write(svd_path, encoding="utf-8", xml_declaration=True)

    structural_errors = validate_file(svd_path)
    cortex_debug_errors = validate_cortex_debug_file(svd_path)
    if structural_errors or cortex_debug_errors:
        details = "\n".join(f"  - {error}" for error in [*structural_errors, *cortex_debug_errors])
        raise SystemExit(f"patched SVD validation failed for {device}:\n{details}")

    metadata_path = ROOT / "metadata" / f"{device.lower()}.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["svd_sha256"] = sha256(svd_path)
        metadata["patch_file"] = str(config_path.relative_to(ROOT))
        metadata["patch_applied"] = changed
        metadata["cmsis_svd_valid"] = True
        metadata["cortex_debug_compatible"] = True
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    status = "patched" if changed else "checked"
    print(f"{status} {svd_path.relative_to(ROOT)}")


def main() -> int:
    for config in sorted((ROOT / "devices").glob("*.yaml")):
        patch_file(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
