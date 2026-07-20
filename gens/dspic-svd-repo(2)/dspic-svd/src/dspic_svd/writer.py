from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .model import Device


def _sub(parent: ET.Element, tag: str, text: str | int | None) -> ET.Element:
    node = ET.SubElement(parent, tag)
    if text is not None:
        node.text = str(text)
    return node


def device_to_tree(device: Device) -> ET.ElementTree:
    root = ET.Element(
        "device",
        {
            "schemaVersion": "1.3",
            "xmlns:xs": "http://www.w3.org/2001/XMLSchema-instance",
            "xs:noNamespaceSchemaLocation": "CMSIS-SVD.xsd",
        },
    )
    _sub(root, "vendor", device.vendor)
    _sub(root, "vendorID", "Microchip")
    _sub(root, "name", device.name)
    _sub(root, "series", device.name.split("128")[0].rstrip("0123456789") or "dsPIC")
    _sub(root, "version", "1.0")
    _sub(root, "description", device.description)
    _sub(root, "licenseText", "Derived from Microchip Device Family Pack data; see metadata.")
    _sub(root, "addressUnitBits", device.address_unit_bits)
    _sub(root, "width", device.width)
    _sub(root, "size", device.width)
    _sub(root, "access", "read-write")
    _sub(root, "resetValue", "0x0")
    _sub(root, "resetMask", hex((1 << device.width) - 1))

    peripherals = ET.SubElement(root, "peripherals")
    peripheral = ET.SubElement(peripherals, "peripheral")
    _sub(peripheral, "name", "SFR")
    _sub(peripheral, "description", "Special Function Register data space")
    _sub(peripheral, "groupName", "SFR")
    _sub(peripheral, "baseAddress", "0x0")
    if device.registers:
        register_extent = max(
            register.address + max(1, (register.size + 7) // 8) for register in device.registers
        )
        address_block = ET.SubElement(peripheral, "addressBlock")
        _sub(address_block, "offset", "0x0")
        _sub(address_block, "size", hex(register_extent))
        _sub(address_block, "usage", "registers")
    if device.interrupts:
        for interrupt in device.interrupts:
            inode = ET.SubElement(peripheral, "interrupt")
            _sub(inode, "name", interrupt.name)
            _sub(inode, "description", interrupt.description or interrupt.name)
            _sub(inode, "value", interrupt.value)
    registers = ET.SubElement(peripheral, "registers")
    for register in device.registers:
        rnode = ET.SubElement(registers, "register")
        _sub(rnode, "name", register.name)
        _sub(rnode, "displayName", register.name)
        _sub(rnode, "description", register.description or register.name)
        _sub(rnode, "addressOffset", hex(register.address))
        _sub(rnode, "size", register.size)
        _sub(rnode, "access", register.access)
        _sub(rnode, "resetValue", hex(register.reset_value))
        if register.reset_mask is not None:
            _sub(rnode, "resetMask", hex(register.reset_mask))
        if register.fields:
            fields = ET.SubElement(rnode, "fields")
            for field in register.fields:
                fnode = ET.SubElement(fields, "field")
                _sub(fnode, "name", field.name)
                _sub(fnode, "description", field.description or field.name)
                _sub(fnode, "bitOffset", field.bit_offset)
                _sub(fnode, "bitWidth", field.bit_width)
                if field.access:
                    _sub(fnode, "access", field.access)
                if field.enums:
                    evs = ET.SubElement(fnode, "enumeratedValues")
                    _sub(evs, "name", f"{register.name}_{field.name}_VALUES")
                    for enum in field.enums:
                        ev = ET.SubElement(evs, "enumeratedValue")
                        _sub(ev, "name", enum.name)
                        _sub(ev, "description", enum.description or enum.name)
                        _sub(ev, "value", hex(enum.value))
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def write_device(device: Device, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tree = device_to_tree(device)
    tree.write(output, encoding="utf-8", xml_declaration=True)
