from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_flash_driver_uses_standard_openocd_callbacks() -> None:
    source = (ROOT / "openocd/overlay/src/flash/nor/mchp_ri4.c").read_text(
        encoding="utf-8"
    )

    assert 'const struct flash_driver mchp_ri4_flash' in source
    assert '.name = "mchp_ri4"' in source
    assert ".erase = mchp_ri4_flash_erase" in source
    assert ".write = mchp_ri4_flash_write" in source
    assert ".read = default_flash_read" in source
    assert ".verify = mchp_ri4_flash_verify" in source
    assert "mchp_ri4_bridge_mass_erase" in source
    assert "target_write_buffer" in source
    assert "target_read_buffer" in source


def test_target_exports_flash_bridge_api() -> None:
    header = (ROOT / "openocd/overlay/src/target/mchp_ri4_bridge.h").read_text(
        encoding="utf-8"
    )
    source = (ROOT / "openocd/overlay/src/target/mchp_ri4_bridge.c").read_text(
        encoding="utf-8"
    )

    assert "mchp_ri4_bridge_is_target" in header
    assert "mchp_ri4_bridge_mass_erase" in header
    assert "int mchp_ri4_bridge_mass_erase" in source


def test_e2e_harness_uses_standard_flash_commands() -> None:
    source = (ROOT / "renode/run_openocd_e2e.py").read_text(encoding="utf-8")

    assert '"flash info 0"' in source
    assert '"flash erase_sector 0 0 last"' in source
    assert 'image_command("flash write_image"' in source
    assert 'image_command("verify_image"' in source
    assert 'f"mchp_ri4 program' not in source
