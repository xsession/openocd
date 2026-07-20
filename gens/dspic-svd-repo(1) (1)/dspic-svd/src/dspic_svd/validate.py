from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .util import local_name, parse_int


class ValidationError(ValueError):
    pass


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"]
    if local_name(root.tag) != "device":
        errors.append("root element must be <device>")
    required = {"name", "version", "description", "addressUnitBits", "width", "peripherals"}
    present = {local_name(child.tag) for child in root}
    for missing in sorted(required - present):
        errors.append(f"missing device element: {missing}")
    register_keys: set[tuple[str, int]] = set()
    for peripheral in (n for n in root.iter() if local_name(n.tag) == "peripheral"):
        pname = next((c.text or "" for c in peripheral if local_name(c.tag) == "name"), "")
        base = parse_int(
            next((c.text for c in peripheral if local_name(c.tag) == "baseAddress"), "0")
        )
        for register in (n for n in peripheral.iter() if local_name(n.tag) == "register"):
            rname = next((c.text or "" for c in register if local_name(c.tag) == "name"), "")
            offset = parse_int(
                next((c.text for c in register if local_name(c.tag) == "addressOffset"), "0")
            )
            key = (pname, base + offset)
            if key in register_keys:
                errors.append(f"duplicate register address in {pname}: 0x{base + offset:x}")
            register_keys.add(key)
            size = parse_int(next((c.text for c in register if local_name(c.tag) == "size"), "16"))
            field_mask = 0
            for field in (n for n in register.iter() if local_name(n.tag) == "field"):
                bit_offset = parse_int(
                    next((c.text for c in field if local_name(c.tag) == "bitOffset"), "0")
                )
                bit_width = parse_int(
                    next((c.text for c in field if local_name(c.tag) == "bitWidth"), "0")
                )
                if bit_width <= 0 or bit_offset + bit_width > size:
                    errors.append(f"invalid field range in {rname}")
                    continue
                mask = ((1 << bit_width) - 1) << bit_offset
                if field_mask & mask:
                    errors.append(f"overlapping fields in {rname}")
                field_mask |= mask
    if not register_keys:
        errors.append("no registers found")
    return errors
