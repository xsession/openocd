from __future__ import annotations

from pathlib import Path
import re
from xml.etree import ElementTree as ET

from .model import Device, EnumValue, Field, Interrupt, Register
from .util import (
    attrs_by_local,
    first_attr,
    infer_access,
    local_name,
    parse_int,
    reset_from_pattern,
    sanitize_identifier,
)


def _desc(element: ET.Element) -> str:
    return (first_attr(element, "desc", "caption", "description", default="") or "").strip()


def _semantic_value(raw: str) -> int:
    try:
        return parse_int(raw)
    except ValueError:
        # EDC commonly stores semantics as expressions such as
        # "(field & 0x3) == 0x02". The final literal is the field value.
        values = re.findall(r"(?<![A-Za-z0-9_])(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|\d+)", raw)
        if not values:
            raise
        return parse_int(values[-1])


def _field_enums(field_element: ET.Element, mask: int) -> list[EnumValue]:
    values: list[EnumValue] = []
    offset = (mask & -mask).bit_length() - 1 if mask else 0
    for node in field_element.iter():
        if node is field_element:
            continue
        lname = local_name(node.tag).lower()
        if "semantic" not in lname and lname not in {"value", "enum", "enumeratedvalue"}:
            continue
        attrs = attrs_by_local(node)
        raw = attrs.get("value") or attrs.get("when") or attrs.get("val")
        if raw is None:
            continue
        try:
            value = _semantic_value(raw)
        except ValueError:
            continue
        if mask and value & mask:
            value = (value & mask) >> offset
        name = attrs.get("cname") or attrs.get("name") or attrs.get("caption") or f"VALUE_{value}"
        values.append(EnumValue(sanitize_identifier(name), value, _desc(node)))
    unique: dict[tuple[str, int], EnumValue] = {}
    for item in values:
        unique[(item.name, item.value)] = item
    return list(unique.values())


def _mode_fields(mode: ET.Element, register_width: int) -> list[Field]:
    fields: list[Field] = []
    occupied = 0
    cursor = 0
    for node in mode:
        lname = local_name(node.tag)
        if lname == "AdjustPoint":
            cursor += parse_int(first_attr(node, "offset"), 0)
            continue
        if lname != "SFRFieldDef":
            continue
        attrs = attrs_by_local(node)
        raw_name = attrs.get("cname") or attrs.get("name")
        if not raw_name:
            continue
        raw_mask = attrs.get("mask")
        if raw_mask is not None:
            try:
                mask = parse_int(raw_mask)
            except ValueError:
                continue
        else:
            field_width = parse_int(attrs.get("nzwidth") or attrs.get("width"), 1)
            if field_width <= 0:
                continue
            mask = ((1 << field_width) - 1) << cursor
        mask &= (1 << register_width) - 1
        if mask == 0 or occupied & mask:
            continue
        occupied |= mask
        cursor = max(cursor, mask.bit_length())
        fields.append(
            Field(
                name=sanitize_identifier(raw_name),
                mask=mask,
                description=_desc(node),
                access=infer_access(attrs.get("access")) if attrs.get("access") else None,
                enums=_field_enums(node, mask),
            )
        )
    return sorted(fields, key=lambda item: (item.bit_offset, item.name))


def _select_mode(register_element: ET.Element) -> ET.Element:
    modes = [node for node in register_element.iter() if local_name(node.tag) == "SFRMode"]
    for mode in modes:
        if (first_attr(mode, "id", default="") or "").upper() == "DS.0":
            return mode
    return modes[0] if modes else register_element


def parse_edc(path: Path, device_name: str | None = None) -> Device:
    root = ET.parse(path).getroot()
    root_attrs = attrs_by_local(root)
    detected_name = device_name or root_attrs.get("cname") or root_attrs.get("name") or path.stem
    registers: list[Register] = []
    seen_addresses: set[int] = set()

    for node in root.iter():
        if local_name(node.tag) != "SFRDef":
            continue
        attrs = attrs_by_local(node)
        raw_name = attrs.get("cname") or attrs.get("name")
        raw_addr = attrs.get("_addr") or attrs.get("addr") or attrs.get("_begin")
        if not raw_name or raw_addr is None:
            continue
        try:
            address = parse_int(raw_addr)
        except ValueError:
            continue
        name = sanitize_identifier(raw_name)
        if address in seen_addresses:
            continue
        seen_addresses.add(address)
        width = parse_int(attrs.get("nzwidth") or attrs.get("width"), 16)
        if width <= 0 or width > 64:
            width = 16
        reset_value, reset_mask = reset_from_pattern(attrs.get("por") or attrs.get("reset"), width)
        mode = _select_mode(node)
        fields = _mode_fields(mode, width)
        registers.append(
            Register(
                name=name,
                address=address,
                size=width,
                description=_desc(node),
                access=infer_access(attrs.get("access")),
                reset_value=reset_value,
                reset_mask=reset_mask,
                fields=fields,
            )
        )

    interrupts: list[Interrupt] = []
    used_interrupt_values: set[int] = set()
    for node in root.iter():
        lname = local_name(node.tag).lower()
        if "interrupt" not in lname or lname in {"interruptlist", "interrupts"}:
            continue
        attrs = attrs_by_local(node)
        raw_name = attrs.get("cname") or attrs.get("name")
        raw_value = attrs.get("irq") or attrs.get("value") or attrs.get("index")
        if not raw_name or raw_value is None:
            continue
        try:
            value = parse_int(raw_value)
        except ValueError:
            continue
        if value in used_interrupt_values:
            continue
        used_interrupt_values.add(value)
        interrupts.append(Interrupt(sanitize_identifier(raw_name), value, _desc(node)))

    if not registers:
        raise ValueError(f"No EDC SFRDef registers found in {path}")
    return Device(
        name=detected_name,
        description=f"Microchip {detected_name} dsPIC Digital Signal Controller",
        registers=sorted(registers, key=lambda item: (item.address, item.name)),
        interrupts=sorted(interrupts, key=lambda item: item.value),
    )
