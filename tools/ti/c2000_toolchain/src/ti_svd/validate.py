from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from .util import local_name, parse_int


ARM_CORTEX_SVD_CPUS = {
    "CM0", "CM0PLUS", "CM1", "SC000", "CM3", "CM4", "CM7",
    "CM23", "CM33", "CM35P", "CM52", "CM55", "CM85",
}
VALID_REGISTER_SIZES = {8, 16, 32, 64}


@dataclass(slots=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    peripheral_count: int
    register_count: int
    field_count: int

    @property
    def ok(self) -> bool:
        return not self.errors


def _direct_text(element: ET.Element, name: str) -> str | None:
    wanted = name.lower()
    for child in element:
        if local_name(child.tag) == wanted:
            text = (child.text or "").strip()
            return text or None
    return None


def _field_range(field: ET.Element) -> tuple[int, int] | None:
    offset = parse_int(_direct_text(field, "bitOffset"))
    width = parse_int(_direct_text(field, "bitWidth"))
    if offset is not None and width is not None:
        return offset, width
    lsb = parse_int(_direct_text(field, "lsb"))
    msb = parse_int(_direct_text(field, "msb"))
    if lsb is not None and msb is not None and msb >= lsb:
        return lsb, msb - lsb + 1
    bit_range = _direct_text(field, "bitRange")
    if bit_range:
        match = re.fullmatch(r"\[(\d+)\s*:\s*(\d+)\]", bit_range)
        if match:
            msb_value, lsb_value = int(match.group(1)), int(match.group(2))
            if msb_value >= lsb_value:
                return lsb_value, msb_value - lsb_value + 1
    return None


def _inherited_int(
    element: ET.Element,
    name: str,
    parent_map: dict[ET.Element, ET.Element],
    default: int | None = None,
) -> int | None:
    current: ET.Element | None = element
    while current is not None:
        value = parse_int(_direct_text(current, name))
        if value is not None:
            return value
        current = parent_map.get(current)
    return default


def validate_svd(
    path: Path,
    *,
    require_cortex_debug: bool = False,
    expected_core: str | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return ValidationResult([str(exc)], [], 0, 0, 0)

    if local_name(root.tag) != "device":
        errors.append("root element is not <device>")

    parent_map = {child: parent for parent in root.iter() for child in parent}

    address_unit_bits = parse_int(_direct_text(root, "addressUnitBits"), 8) or 8
    if require_cortex_debug and address_unit_bits != 8:
        errors.append(
            f"Cortex-Debug/Peripheral Viewer expects byte-addressable SVD data; addressUnitBits is {address_unit_bits}"
        )

    cpu = next((child for child in root if local_name(child.tag) == "cpu"), None)
    cpu_name = (_direct_text(cpu, "name") if cpu is not None else None) or ""
    if expected_core and expected_core in ARM_CORTEX_SVD_CPUS and cpu_name != expected_core:
        errors.append(f"CPU name is '{cpu_name or 'missing'}', expected '{expected_core}'")
    if require_cortex_debug:
        if not cpu_name:
            errors.append("Cortex-Debug target SVD has no <cpu><name> entry")
        elif cpu_name not in ARM_CORTEX_SVD_CPUS:
            errors.append(f"CPU '{cpu_name}' is not an Arm Cortex-M CPU supported by this compatibility profile")

    peripherals = [element for element in root.iter() if local_name(element.tag) == "peripheral"]
    registers = [element for element in root.iter() if local_name(element.tag) == "register"]
    fields = [element for element in root.iter() if local_name(element.tag) == "field"]
    if not peripherals:
        errors.append("no peripherals")
    if not registers:
        errors.append("no registers")

    seen_peripheral_names: set[str] = set()
    seen_peripheral_addresses: set[tuple[str, int]] = set()
    for peripheral in peripherals:
        name = _direct_text(peripheral, "name") or ""
        base = parse_int(_direct_text(peripheral, "baseAddress"), -1)
        if not name:
            errors.append("peripheral without name")
        elif name in seen_peripheral_names:
            errors.append(f"duplicate peripheral name '{name}'")
        seen_peripheral_names.add(name)
        if base is None or base < 0:
            errors.append(f"peripheral '{name or '?'}' has invalid baseAddress")
            base = -1
        key = (name, base)
        if key in seen_peripheral_addresses:
            warnings.append(f"duplicate peripheral identity {name} at 0x{base:X}")
        seen_peripheral_addresses.add(key)

        register_names: set[str] = set()
        for register in peripheral.iter():
            if local_name(register.tag) != "register":
                continue
            register_name = _direct_text(register, "name") or ""
            if not register_name:
                errors.append(f"peripheral '{name or '?'}' contains a register without a name")
            elif register_name in register_names:
                warnings.append(f"peripheral '{name}' contains repeated register name '{register_name}'")
            register_names.add(register_name)

            offset = parse_int(_direct_text(register, "addressOffset"))
            if offset is None or offset < 0:
                errors.append(f"register '{name}.{register_name or '?'}' has invalid addressOffset")

            size = _inherited_int(register, "size", parent_map, 32) or 0
            if size not in VALID_REGISTER_SIZES:
                errors.append(f"register '{name}.{register_name or '?'}' has unsupported size {size}")

            reset_value = parse_int(_direct_text(register, "resetValue"))
            reset_mask = parse_int(_direct_text(register, "resetMask"))
            if size > 0:
                maximum = (1 << size) - 1
                if reset_value is not None and reset_value > maximum:
                    errors.append(f"register '{name}.{register_name}' resetValue does not fit {size} bits")
                if reset_mask is not None and reset_mask > maximum:
                    errors.append(f"register '{name}.{register_name}' resetMask does not fit {size} bits")

            field_names: set[str] = set()
            for field in register.iter():
                if local_name(field.tag) != "field":
                    continue
                field_name = _direct_text(field, "name") or ""
                if not field_name:
                    errors.append(f"register '{name}.{register_name}' contains a field without a name")
                elif field_name in field_names:
                    warnings.append(f"register '{name}.{register_name}' contains repeated field name '{field_name}'")
                field_names.add(field_name)
                bit_range = _field_range(field)
                if bit_range is None:
                    errors.append(f"field '{name}.{register_name}.{field_name or '?'}' has no valid bit range")
                    continue
                bit_offset, bit_width = bit_range
                if bit_offset < 0 or bit_width <= 0 or bit_offset + bit_width > size:
                    errors.append(
                        f"field '{name}.{register_name}.{field_name or '?'}' range "
                        f"[{bit_offset + bit_width - 1}:{bit_offset}] exceeds {size}-bit register"
                    )

    return ValidationResult(errors, warnings, len(peripherals), len(registers), len(fields))
