from pathlib import Path

from dspic_svd.edc import parse_edc


def test_parse_edc_fixture():
    path = Path(__file__).parent / "fixtures" / "minimal-dspic.PIC"
    device = parse_edc(path)
    assert device.name == "dsPICTest"
    assert len(device.registers) == 2
    timer = device.registers[0]
    assert timer.name == "T1CON"
    assert timer.address == 0x100
    assert timer.size == 16
    assert [field.name for field in timer.fields] == ["TCS", "TON"]
    assert timer.fields[1].bit_offset == 15
    assert timer.fields[1].bit_width == 1
    assert [enum.name for enum in timer.fields[1].enums] == ["OFF", "ON"]


def test_parse_implicit_field_positions_and_semantics():
    path = Path(__file__).parent / "fixtures" / "implicit-fields.PIC"
    device = parse_edc(path)
    register = device.registers[0]
    assert register.access == "read-write"
    assert [(field.name, field.bit_offset, field.bit_width) for field in register.fields] == [
        ("MODE", 2, 2),
        ("ENABLE", 5, 1),
    ]
    assert [(enum.name, enum.value) for enum in register.fields[0].enums] == [
        ("MODE_A", 0),
        ("MODE_B", 2),
    ]
