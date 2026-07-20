import tomllib
from pathlib import Path


def test_manifest_has_requested_devices():
    root = Path(__file__).resolve().parents[1]
    with (root / "packs.toml").open("rb") as handle:
        data = tomllib.load(handle)
    devices = {device for pack in data["packs"] for device in pack["devices"]}
    assert devices == {
        "dsPIC30F5011",
        "dsPIC33FJ128MC802",
        "dsPIC33FJ128MC804",
        "dsPIC33EP128GM604",
    }
