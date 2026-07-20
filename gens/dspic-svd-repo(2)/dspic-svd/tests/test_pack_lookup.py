import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from update_packs import descriptor_stems, find_member  # noqa: E402


def test_descriptor_stems_support_xc16_names():
    assert descriptor_stems("dsPIC30F5011") == {"dspic30f5011", "p30f5011"}
    assert descriptor_stems("dsPIC33FJ128MC802") == {
        "dspic33fj128mc802",
        "p33fj128mc802",
    }


def test_find_member_accepts_p_prefixed_pic_name():
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("edc/p33FJ128MC802.PIC", "<device/>")
    payload.seek(0)
    with ZipFile(payload) as archive:
        assert find_member(archive, "dsPIC33FJ128MC802") == "edc/p33FJ128MC802.PIC"
