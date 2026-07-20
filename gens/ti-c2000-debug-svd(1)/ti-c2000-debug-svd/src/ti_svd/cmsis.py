from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .models import DeviceManifest, Peripheral
from .util import indent_xml


def _text(parent: ET.Element, tag: str, value: object) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child


def _hex(value: int, width: int = 8) -> str:
    return f"0x{value:0{width}X}"


def build_svd(manifest: DeviceManifest, peripherals: list[Peripheral], source_note: str) -> ET.Element:
    device = ET.Element("device", {
        "schemaVersion": "1.3",
        "xmlns:xs": "http://www.w3.org/2001/XMLSchema-instance",
        "xs:noNamespaceSchemaLocation": "CMSIS-SVD.xsd",
    })
    _text(device, "vendor", manifest.vendor)
    _text(device, "vendorID", "TI")
    _text(device, "name", manifest.name)
    _text(device, "series", manifest.family)
    _text(device, "version", "0.2.0-generated")
    _text(device, "description", f"Generated from {source_note}. Review against the TI technical reference manual before production use.")
    _text(device, "licenseText", "Generated metadata follows the license of the source TI files. Generator code is MIT licensed.")
    if manifest.core in {"CM0", "CM0PLUS", "CM3", "CM4", "CM7"}:
        cpu = ET.SubElement(device, "cpu")
        cpu_names = {"CM0": "CM0", "CM0PLUS": "CM0PLUS", "CM3": "CM3", "CM4": "CM4", "CM7": "CM7"}
        _text(cpu, "name", cpu_names[manifest.core])
        _text(cpu, "revision", "r0p0" if manifest.core != "CM3" else "r2p1")
        _text(cpu, "endian", "little")
        _text(cpu, "mpuPresent", "false")
        _text(cpu, "fpuPresent", "false")
        _text(cpu, "nvicPrioBits", "3")
        _text(cpu, "vendorSystickConfig", "false")
    _text(device, "addressUnitBits", manifest.address_unit_bits)
    _text(device, "width", manifest.width)
    _text(device, "size", manifest.width)
    _text(device, "access", "read-write")
    _text(device, "resetValue", "0x00000000")
    _text(device, "resetMask", "0xFFFFFFFF")
    peripherals_node = ET.SubElement(device, "peripherals")
    for peripheral in peripherals:
        pnode = ET.SubElement(peripherals_node, "peripheral")
        _text(pnode, "name", peripheral.name)
        _text(pnode, "description", peripheral.description)
        _text(pnode, "groupName", peripheral.name.rstrip("0123456789_"))
        _text(pnode, "baseAddress", _hex(peripheral.base_address))
        if peripheral.registers:
            rnodes = ET.SubElement(pnode, "registers")
            for register in peripheral.registers:
                rnode = ET.SubElement(rnodes, "register")
                _text(rnode, "name", register.name)
                _text(rnode, "description", register.description)
                _text(rnode, "addressOffset", _hex(register.offset))
                _text(rnode, "size", register.size)
                _text(rnode, "access", register.access)
                _text(rnode, "resetValue", _hex(register.reset_value, max(1, register.size // 4)))
                _text(rnode, "resetMask", _hex((1 << min(register.size, 64)) - 1, max(1, register.size // 4)))
                if register.fields:
                    fnodes = ET.SubElement(rnode, "fields")
                    for field in register.fields:
                        fnode = ET.SubElement(fnodes, "field")
                        _text(fnode, "name", field.name)
                        _text(fnode, "description", field.description)
                        _text(fnode, "bitOffset", field.bit_offset)
                        _text(fnode, "bitWidth", field.bit_width)
                        if field.access:
                            _text(fnode, "access", field.access)
                        if field.enumerated_values:
                            enodes = ET.SubElement(fnode, "enumeratedValues")
                            for name, value, description in field.enumerated_values:
                                enode = ET.SubElement(enodes, "enumeratedValue")
                                _text(enode, "name", name)
                                _text(enode, "description", description)
                                _text(enode, "value", _hex(value, max(1, field.bit_width // 4)))
        for name, value, description in peripheral.interrupts:
            inode = ET.SubElement(pnode, "interrupt")
            _text(inode, "name", name)
            _text(inode, "description", description)
            _text(inode, "value", value)
    vendor_ext = ET.SubElement(device, "vendorExtensions")
    _text(vendor_ext, "tiCore", manifest.core)
    _text(vendor_ext, "tiAddressScale", manifest.address_scale)
    _text(vendor_ext, "tiCortexDebugCompatible", str(manifest.cortex_debug).lower())
    _text(vendor_ext, "tiProcessorName", manifest.processor_name)
    _text(vendor_ext, "tiGenerator", "ti-c2000-mspm0-svd")
    return device


def write_svd(root: ET.Element, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    indent_xml(root)
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
