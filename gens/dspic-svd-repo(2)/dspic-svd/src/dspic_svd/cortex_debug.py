from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .util import local_name, parse_int

_ALLOWED_ACCESS = {
    "read-only",
    "read-write",
    "write-only",
    "read-writeOnce",
    "writeOnce",
}


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in parent if local_name(child.tag) == name]


def _child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in parent if local_name(child.tag) == name), None)


def _text(parent: ET.Element, name: str, default: str | None = None) -> str | None:
    node = _child(parent, name)
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _integer(
    parent: ET.Element,
    name: str,
    errors: list[str],
    context: str,
    *,
    required: bool = True,
    default: int | None = None,
) -> int | None:
    raw = _text(parent, name)
    if raw is None:
        if required:
            errors.append(f"{context}: missing <{name}>")
        return default
    try:
        return parse_int(raw)
    except ValueError:
        errors.append(f"{context}: invalid integer in <{name}>: {raw!r}")
        return default


def _validate_access(parent: ET.Element, errors: list[str], context: str) -> None:
    access = _text(parent, "access")
    if access is not None and access not in _ALLOWED_ACCESS:
        errors.append(f"{context}: unsupported Cortex-Debug access value {access!r}")


def validate_cortex_debug_file(path: Path) -> list[str]:
    """Validate the subset consumed by Cortex-Debug's MCU Peripheral Viewer.

    The viewer parses SVD through xml2js and directly indexes the device,
    peripheral, register, and field arrays. This validator intentionally checks
    that concrete shape rather than only checking broad CMSIS-SVD validity.
    """

    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"]

    if local_name(root.tag) != "device":
        return ["root element must be <device>"]

    device_name = _text(root, "name", path.stem) or path.stem
    context = f"device {device_name}"

    address_unit_bits = _integer(root, "addressUnitBits", errors, context)
    if address_unit_bits is not None and address_unit_bits != 8:
        errors.append(
            f"{context}: addressUnitBits must be 8 because Cortex-Debug treats "
            "baseAddress/addressOffset as byte addresses"
        )

    device_size = _integer(root, "size", errors, context)
    if device_size is not None and device_size <= 0:
        errors.append(f"{context}: device size must be positive")
    _validate_access(root, errors, context)
    _integer(root, "resetValue", errors, context)

    peripherals_nodes = _children(root, "peripherals")
    if len(peripherals_nodes) != 1:
        errors.append(f"{context}: expected exactly one <peripherals> container")
        return errors

    peripherals = _children(peripherals_nodes[0], "peripheral")
    if not peripherals:
        errors.append(f"{context}: no peripherals defined")
        return errors

    peripheral_names: set[str] = set()
    for peripheral in peripherals:
        pname = _text(peripheral, "name")
        if not pname:
            errors.append(f"{context}: peripheral missing name")
            pname = "<unnamed>"
        pcontext = f"{context}, peripheral {pname}"
        if pname in peripheral_names:
            errors.append(f"{pcontext}: duplicate peripheral name")
        peripheral_names.add(pname)

        base_address = _integer(peripheral, "baseAddress", errors, pcontext, default=0)
        if base_address is not None and base_address < 0:
            errors.append(f"{pcontext}: negative baseAddress")
        _validate_access(peripheral, errors, pcontext)

        registers_nodes = _children(peripheral, "registers")
        if len(registers_nodes) != 1:
            errors.append(f"{pcontext}: expected exactly one <registers> container")
            continue
        registers = _children(registers_nodes[0], "register")
        if not registers:
            errors.append(f"{pcontext}: no registers defined")
            continue

        register_names: set[str] = set()
        ranges: list[tuple[int, int, str]] = []
        highest_end = 0
        for register in registers:
            rname = _text(register, "name")
            if not rname:
                errors.append(f"{pcontext}: register missing name")
                rname = "<unnamed>"
            rcontext = f"{pcontext}, register {rname}"
            if rname in register_names:
                errors.append(f"{rcontext}: duplicate register name")
            register_names.add(rname)

            offset = _integer(register, "addressOffset", errors, rcontext)
            size = _integer(register, "size", errors, rcontext, default=device_size)
            _validate_access(register, errors, rcontext)
            reset_value = _integer(register, "resetValue", errors, rcontext, default=0)

            if offset is None or size is None:
                continue
            if offset < 0:
                errors.append(f"{rcontext}: negative addressOffset")
            if size <= 0 or size % 8 != 0:
                errors.append(f"{rcontext}: size must be a positive multiple of 8 bits")
                byte_size = 0
            else:
                byte_size = size // 8
            if reset_value is not None and size > 0 and reset_value >= (1 << size):
                errors.append(f"{rcontext}: resetValue does not fit in {size} bits")

            absolute = (base_address or 0) + offset
            end = absolute + byte_size
            highest_end = max(highest_end, offset + byte_size)
            for other_start, other_end, other_name in ranges:
                if byte_size and absolute < other_end and other_start < end:
                    errors.append(
                        f"{rcontext}: byte range 0x{absolute:x}-0x{end - 1:x} overlaps "
                        f"register {other_name}"
                    )
            ranges.append((absolute, end, rname))

            fields_nodes = _children(register, "fields")
            if len(fields_nodes) > 1:
                errors.append(f"{rcontext}: multiple <fields> containers are unsupported")
            fields = _children(fields_nodes[0], "field") if fields_nodes else []
            field_names: set[str] = set()
            field_mask = 0
            for field in fields:
                fname = _text(field, "name")
                if not fname:
                    errors.append(f"{rcontext}: field missing name")
                    fname = "<unnamed>"
                fcontext = f"{rcontext}, field {fname}"
                if fname in field_names:
                    errors.append(f"{fcontext}: duplicate field name")
                field_names.add(fname)

                bit_offset = _integer(field, "bitOffset", errors, fcontext)
                bit_width = _integer(field, "bitWidth", errors, fcontext)
                _validate_access(field, errors, fcontext)
                if bit_offset is None or bit_width is None or size is None:
                    continue
                if bit_offset < 0 or bit_width <= 0 or bit_offset + bit_width > size:
                    errors.append(f"{fcontext}: invalid bit range")
                    continue
                mask = ((1 << bit_width) - 1) << bit_offset
                if field_mask & mask:
                    errors.append(f"{fcontext}: overlaps another field")
                field_mask |= mask

                enum_groups = _children(field, "enumeratedValues")
                if len(enum_groups) > 1:
                    errors.append(
                        f"{fcontext}: multiple enumeratedValues groups are avoided for "
                        "maximum Cortex-Debug compatibility"
                    )
                for enum_group in enum_groups:
                    for enum_value in _children(enum_group, "enumeratedValue"):
                        ename = _text(enum_value, "name")
                        if not ename:
                            errors.append(f"{fcontext}: enumeratedValue missing name")
                        value = _integer(
                            enum_value,
                            "value",
                            errors,
                            f"{fcontext}, enum {ename or '<unnamed>'}",
                        )
                        if value is not None and (value < 0 or value >= (1 << bit_width)):
                            errors.append(
                                f"{fcontext}: enum {ename or '<unnamed>'} value {value} "
                                f"does not fit in {bit_width} bits"
                            )

        address_blocks = _children(peripheral, "addressBlock")
        if address_blocks:
            block = address_blocks[0]
            block_offset = _integer(block, "offset", errors, pcontext)
            block_size = _integer(block, "size", errors, pcontext)
            usage = _text(block, "usage")
            if usage != "registers":
                errors.append(f"{pcontext}: addressBlock usage must be 'registers'")
            if block_offset is not None and block_offset != 0:
                errors.append(f"{pcontext}: generated addressBlock offset must be zero")
            if block_size is not None and block_size < highest_end:
                errors.append(
                    f"{pcontext}: addressBlock size 0x{block_size:x} does not cover "
                    f"register extent 0x{highest_end:x}"
                )
        else:
            errors.append(f"{pcontext}: missing addressBlock used by Cortex-Debug range planning")

    return errors
