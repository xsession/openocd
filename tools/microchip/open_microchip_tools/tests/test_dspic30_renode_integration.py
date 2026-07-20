from __future__ import annotations

from pathlib import Path

from mchp_simulator.firmware_image import FirmwareImage, Segment
from renode.run_openocd_e2e import CORE_CONFIG, image_command, openocd_image_offset


ROOT = Path(__file__).parents[1]


def test_dspic30_platform_matches_custom_core_memory_window() -> None:
    repl = (ROOT / "renode/platforms/dspic30_openocd.repl").read_text(encoding="utf-8")
    resc = (ROOT / "renode/platforms/dspic30_openocd.resc").read_text(encoding="utf-8")

    assert "cpu: CPU.DSPIC33 @ sysbus" in repl
    assert 'cpuType: "dspic30f5011"' in repl
    assert "flash: Memory.MappedMemory @ sysbus 0x100000" in repl
    assert "size: 0x00AC00" in repl
    assert "ram: Memory.MappedMemory @ sysbus 0x001000" in repl
    assert "machine LoadPlatformDescription @dspic30_openocd.repl" in resc


def test_dspic30_e2e_profile_and_logical_image_offset(tmp_path: Path) -> None:
    cfg = CORE_CONFIG["dspic30"]
    image_path = tmp_path / "logical.hex"
    FirmwareImage(segments=(Segment(0, b"\x01\x02\x03\x04"),)).to_intel_hex_path(
        str(image_path)
    )

    offset = openocd_image_offset(
        image_path,
        image_bias=cfg["image_bias"],
        flash_size=cfg["flash_size"],
    )
    assert offset == 0x100000
    assert image_command("flash write_image", image_path, offset).endswith("} 0x100000")
    assert cfg["watch"] == 0x1000


def test_dspic30_already_rebased_image_is_not_shifted_twice(tmp_path: Path) -> None:
    cfg = CORE_CONFIG["dspic30"]
    image_path = tmp_path / "rebased.hex"
    FirmwareImage(segments=(Segment(0x100000, b"\xAA\x55"),)).to_intel_hex_path(str(image_path))

    assert (
        openocd_image_offset(
            image_path,
            image_bias=cfg["image_bias"],
            flash_size=cfg["flash_size"],
        )
        == 0
    )
