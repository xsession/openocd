from pathlib import Path
from xml.etree import ElementTree as ET

from dspic_svd.convert import convert_file
from dspic_svd.cortex_debug import validate_cortex_debug_file


def _generated_svd(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "minimal-dspic.PIC"
    target = tmp_path / "test.svd"
    convert_file(source, target)
    return target


def test_generated_svd_matches_cortex_debug_parser_shape(tmp_path: Path):
    target = _generated_svd(tmp_path)

    assert validate_cortex_debug_file(target) == []

    tree = ET.parse(target)
    root = tree.getroot()
    peripheral = root.find("./peripherals/peripheral")
    assert peripheral is not None
    assert peripheral.findtext("groupName") == "SFR"
    assert peripheral.findtext("addressBlock/usage") == "registers"

    timer = peripheral.find("./registers/register[name='T1CON']")
    assert timer is not None
    assert timer.findtext("displayName") == "T1CON"
    assert timer.findtext("fields/field[name='TON']/enumeratedValues/name") == ("T1CON_TON_VALUES")


def test_non_byte_address_units_are_rejected_for_cortex_debug(tmp_path: Path):
    target = _generated_svd(tmp_path)
    tree = ET.parse(target)
    root = tree.getroot()
    address_unit_bits = root.find("addressUnitBits")
    assert address_unit_bits is not None
    address_unit_bits.text = "16"
    tree.write(target, encoding="utf-8", xml_declaration=True)

    errors = validate_cortex_debug_file(target)
    assert any("addressUnitBits must be 8" in error for error in errors)
