from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .model import Device, EnumValue, Field, Register
from .util import (
    attrs_by_local,
    first_attr,
    infer_access,
    local_name,
    parse_int,
    sanitize_identifier,
)


def parse_atdf(path: Path, device_name: str | None = None) -> Device:
    root = ET.parse(path).getroot()
    device_node = next((n for n in root.iter() if local_name(n.tag) == "device"), root)
    detected_name = device_name or first_attr(device_node, "name", default=path.stem) or path.stem

    module_defs: dict[str, ET.Element] = {}
    for module in root.iter():
        if local_name(module.tag) == "module":
            name = first_attr(module, "name")
            if name and any(local_name(n.tag) == "register-group" for n in module):
                module_defs[name] = module

    registers: list[Register] = []
    seen: set[tuple[int, str]] = set()
    for instance in root.iter():
        if local_name(instance.tag) != "instance":
            continue
        instance_name = first_attr(instance, "name", default="PERIPH") or "PERIPH"
        module_name = first_attr(instance, "module", "name-in-module", default="") or ""
        module = module_defs.get(module_name)
        if module is None:
            parent_module = next((m for m in root.iter() if instance in list(m)), None)
            if parent_module is not None:
                module = module_defs.get(first_attr(parent_module, "name", default="") or "")
        if module is None:
            continue
        group_instances = [n for n in instance.iter() if local_name(n.tag) == "register-group"]
        instance_offset = parse_int(first_attr(instance, "offset"), 0)
        for group_instance in group_instances or [instance]:
            group_name = first_attr(group_instance, "name-in-module", "name", default="") or ""
            group_offset = parse_int(first_attr(group_instance, "offset"), 0)
            group_def = next(
                (
                    g
                    for g in module.iter()
                    if local_name(g.tag) == "register-group"
                    and (first_attr(g, "name", default="") or "") == group_name
                ),
                None,
            )
            if group_def is None:
                continue
            for reg in group_def:
                if local_name(reg.tag) != "register":
                    continue
                attrs = attrs_by_local(reg)
                reg_name = attrs.get("name")
                if not reg_name:
                    continue
                address = instance_offset + group_offset + parse_int(attrs.get("offset"), 0)
                full_name = sanitize_identifier(f"{instance_name}_{reg_name}")
                if (address, full_name) in seen:
                    continue
                seen.add((address, full_name))
                width = parse_int(attrs.get("size"), 2) * 8
                fields: list[Field] = []
                for bitfield in reg:
                    if local_name(bitfield.tag) != "bitfield":
                        continue
                    battrs = attrs_by_local(bitfield)
                    mask = parse_int(battrs.get("mask"), 0)
                    if not mask:
                        continue
                    enums: list[EnumValue] = []
                    values_name = battrs.get("values")
                    if values_name:
                        value_group = next(
                            (
                                vg
                                for vg in module.iter()
                                if local_name(vg.tag) == "value-group"
                                and first_attr(vg, "name") == values_name
                            ),
                            None,
                        )
                        if value_group is not None:
                            for value in value_group:
                                vattrs = attrs_by_local(value)
                                if "value" in vattrs:
                                    enums.append(
                                        EnumValue(
                                            sanitize_identifier(vattrs.get("name", "VALUE")),
                                            parse_int(vattrs["value"]),
                                            vattrs.get("caption", ""),
                                        )
                                    )
                    fields.append(
                        Field(
                            sanitize_identifier(battrs.get("name", "FIELD")),
                            mask,
                            battrs.get("caption", ""),
                            enums=enums,
                        )
                    )
                registers.append(
                    Register(
                        name=full_name,
                        address=address,
                        size=width,
                        description=attrs.get("caption", ""),
                        access=infer_access(attrs.get("rw")),
                        reset_value=parse_int(attrs.get("initval"), 0),
                        reset_mask=(1 << width) - 1,
                        fields=fields,
                    )
                )
    if not registers:
        raise ValueError(f"No ATDF registers found in {path}")
    return Device(
        name=detected_name,
        description=f"Microchip {detected_name} dsPIC Digital Signal Controller",
        registers=sorted(registers, key=lambda item: (item.address, item.name)),
    )
