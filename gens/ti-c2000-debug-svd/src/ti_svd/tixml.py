from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import DeviceManifest, Field, Peripheral, Register
from .util import (
    child_property,
    find_case_insensitive,
    first_attr,
    local_name,
    normalize_access,
    parse_int,
    sanitize_identifier,
)

REFERENCE_ATTRS = ("href", "file", "filename", "path", "xml", "module", "src")
BASE_ATTRS = ("baseaddr", "baseaddress", "base", "address", "start")
NAME_ATTRS = ("name", "id", "instance", "identifier", "label")


def _parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"cannot parse TI XML {path}: {exc}") from exc


def _description(element: ET.Element, fallback: str) -> str:
    value = child_property(element, "description", "desc", "caption", "displayname", "title")
    return (value or fallback).strip()


def _resolve_module_path(targetdb: Path, device_xml: Path, reference: str) -> Path | None:
    ref = reference.replace("\\", "/").lstrip("./")
    candidates = [
        device_xml.parent / ref,
        targetdb / ref,
        targetdb / "Modules" / ref,
        targetdb / "modules" / ref,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for base in (device_xml.parent, targetdb, targetdb / "Modules"):
        found = find_case_insensitive(base, ref)
        if found and found.exists():
            return found
    basename = Path(ref).name.lower()
    if basename:
        match = next((p for p in (targetdb / "Modules").rglob("*.xml") if p.name.lower() == basename), None)
        if match:
            return match
    return None


def _module_references(root: ET.Element, targetdb: Path, device_xml: Path, manifest: DeviceManifest) -> list[tuple[str, int, Path]]:
    references: list[tuple[str, int, Path]] = []
    seen: set[tuple[str, int, Path]] = set()
    for element in root.iter():
        ref = first_attr(element, *REFERENCE_ATTRS) or child_property(element, *REFERENCE_ATTRS)
        if not ref or ".xml" not in ref.lower():
            continue
        module_path = _resolve_module_path(targetdb, device_xml, ref)
        if module_path is None or module_path.resolve() == device_xml.resolve():
            continue
        raw_name = first_attr(element, *NAME_ATTRS) or module_path.stem
        base_raw = child_property(element, *BASE_ATTRS)
        base = parse_int(base_raw, 0) or 0
        search_text = f"{raw_name} {ref} {module_path}".upper()
        if manifest.include_tokens and not any(token in search_text for token in manifest.include_tokens):
            # Shared targetdb descriptors often lack a core token. Keep them when a real base exists.
            if base == 0:
                continue
        if any(token in search_text for token in manifest.exclude_tokens):
            continue
        item = (sanitize_identifier(raw_name, module_path.stem), base * manifest.address_scale, module_path)
        if item not in seen:
            seen.add(item)
            references.append(item)
    return references


def _field_bits(element: ET.Element) -> tuple[int, int] | None:
    bits = child_property(element, "bits", "bitrange", "range")
    if bits:
        match = re.search(r"\[?\s*(\d+)\s*:\s*(\d+)\s*\]?", bits)
        if match:
            msb, lsb = int(match.group(1)), int(match.group(2))
            return min(lsb, msb), abs(msb - lsb) + 1
        single = parse_int(bits)
        if single is not None:
            return single, 1
    offset = parse_int(child_property(element, "bitoffset", "offset", "lsb", "begin", "start", "position"))
    width = parse_int(child_property(element, "bitwidth", "width", "length", "size"))
    msb = parse_int(child_property(element, "msb", "end", "stop"))
    if offset is not None and width is not None:
        return offset, max(width, 1)
    if offset is not None and msb is not None:
        return min(offset, msb), abs(msb - offset) + 1
    return None


def _parse_enums(field_element: ET.Element) -> list[tuple[str, int, str]]:
    values: list[tuple[str, int, str]] = []
    seen_names: set[str] = set()
    for element in field_element.iter():
        if element is field_element:
            continue
        tag = local_name(element.tag)
        if tag not in {"enum", "enumeration", "enumeratedvalue", "bitenum", "value", "option", "choice"}:
            continue
        name = first_attr(element, "name", "id", "label")
        value = parse_int(child_property(element, "value", "val", "number"))
        if not name or value is None:
            continue
        clean = sanitize_identifier(name, f"VALUE_{value}")
        if clean in seen_names:
            clean = f"{clean}_{value:X}"
        seen_names.add(clean)
        values.append((clean, value, _description(element, name)))
    return values


def _parse_fields(register_element: ET.Element, register_size: int) -> list[Field]:
    fields: list[Field] = []
    used: set[str] = set()
    for element in register_element.iter():
        if element is register_element or local_name(element.tag) not in {"field", "bitfield", "bit", "registerfield"}:
            continue
        name = first_attr(element, *NAME_ATTRS)
        bit_info = _field_bits(element)
        if not name or bit_info is None:
            continue
        bit_offset, bit_width = bit_info
        if bit_offset < 0 or bit_width <= 0 or bit_offset >= register_size:
            continue
        bit_width = min(bit_width, register_size - bit_offset)
        clean = sanitize_identifier(name)
        if clean in used:
            clean = f"{clean}_{bit_offset}"
        used.add(clean)
        fields.append(Field(
            name=clean,
            description=_description(element, name),
            bit_offset=bit_offset,
            bit_width=bit_width,
            access=normalize_access(child_property(element, "access", "type"), "read-write"),
            enumerated_values=_parse_enums(element),
        ))
    return sorted(fields, key=lambda f: (f.bit_offset, f.name))


def _register_candidates(root: ET.Element) -> list[ET.Element]:
    candidates: list[ET.Element] = []
    for element in root.iter():
        tag = local_name(element.tag)
        if tag not in {"register", "reg", "registerdefinition", "registerinstance"}:
            continue
        name = first_attr(element, *NAME_ATTRS)
        offset = child_property(element, "offset", "addressoffset", "address", "addr", "start")
        if name and offset is not None:
            candidates.append(element)
    return candidates


def parse_module(module_path: Path, instance_name: str, base_address: int, manifest: DeviceManifest) -> Peripheral:
    root = _parse_xml(module_path)
    registers: list[Register] = []
    used: set[tuple[str, int]] = set()
    for element in _register_candidates(root):
        raw_name = first_attr(element, *NAME_ATTRS)
        raw_offset = child_property(element, "offset", "addressoffset", "address", "addr", "start")
        if not raw_name or raw_offset is None:
            continue
        offset_units = parse_int(raw_offset)
        if offset_units is None:
            continue
        # TI module files normally use relative offsets. If an absolute address is present, normalize it.
        scaled = offset_units * manifest.address_scale
        offset = scaled - base_address if base_address and scaled >= base_address else scaled
        size = parse_int(child_property(element, "size", "width", "bits", "registerwidth"), manifest.default_register_width)
        size = size or manifest.default_register_width
        if size in (1, 2, 4, 8) and child_property(element, "bits", "registerwidth") is None:
            size *= 8
        size = min(max(size, 1), 64)
        clean_name = sanitize_identifier(raw_name)
        key = (clean_name, offset)
        if key in used:
            continue
        used.add(key)
        registers.append(Register(
            name=clean_name,
            description=_description(element, raw_name),
            offset=offset,
            size=size,
            access=normalize_access(child_property(element, "access", "type", "rw")),
            reset_value=parse_int(child_property(element, "resetvalue", "reset", "default"), 0) or 0,
            fields=_parse_fields(element, size),
        ))
    peripheral_name = sanitize_identifier(instance_name or module_path.stem)
    return Peripheral(
        name=peripheral_name,
        description=_description(root, peripheral_name),
        base_address=base_address,
        registers=sorted(registers, key=lambda r: (r.offset, r.name)),
        source_path=str(module_path),
    )


def parse_device(device_xml: Path, targetdb: Path, manifest: DeviceManifest) -> list[Peripheral]:
    root = _parse_xml(device_xml)
    references = _module_references(root, targetdb, device_xml, manifest)
    peripherals: list[Peripheral] = []
    for instance_name, base_address, module_path in references:
        peripheral = parse_module(module_path, instance_name, base_address, manifest)
        if peripheral.registers:
            peripherals.append(peripheral)
    if not peripherals:
        fallback = parse_module(device_xml, manifest.name, 0, manifest)
        if fallback.registers:
            peripherals.append(fallback)
    # De-duplicate while preserving same module at different base addresses.
    unique: dict[tuple[str, int], Peripheral] = {}
    for peripheral in peripherals:
        key = (peripheral.name, peripheral.base_address)
        if key not in unique or len(peripheral.registers) > len(unique[key].registers):
            unique[key] = peripheral
    return sorted(unique.values(), key=lambda p: (p.base_address, p.name))
