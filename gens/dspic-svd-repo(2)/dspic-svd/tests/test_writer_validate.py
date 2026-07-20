from pathlib import Path

from dspic_svd.convert import convert_file
from dspic_svd.validate import validate_file


def test_write_and_validate(tmp_path: Path):
    source = Path(__file__).parent / "fixtures" / "minimal-dspic.PIC"
    target = tmp_path / "test.svd"
    convert_file(source, target)
    assert target.exists()
    assert validate_file(target) == []
    text = target.read_text(encoding="utf-8")
    assert "<name>T1CON</name>" in text
    assert "<addressOffset>0x100</addressOffset>" in text
