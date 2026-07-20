from pathlib import Path

import pytest

from openocd.install_overlay import install


@pytest.mark.parametrize(
    ("testee_path", "bridge_path"),
    [
        ("%D%/testee.c", "%D%/mchp_ri4_bridge.c"),
        ("%D%/target/testee.c", "%D%/target/mchp_ri4_bridge.c"),
    ],
)
def test_installer_copies_and_registers_overlay(
    tmp_path: Path,
    testee_path: str,
    bridge_path: str,
) -> None:
    tree = tmp_path / "openocd"
    (tree / "src/target").mkdir(parents=True)
    (tree / "src/flash/nor").mkdir(parents=True)
    (tree / "tcl/interface").mkdir(parents=True)
    (tree / "tcl/target").mkdir(parents=True)
    (tree / "src/target/Makefile.am").write_text(
        f"libtarget_la_SOURCES = \\\n\t{testee_path} \\\n\t$(NULL)\n",
        encoding="utf-8",
    )
    (tree / "src/target/target_type.h").write_text(
        "extern struct target_type mips_m4k_target;\n",
        encoding="utf-8",
    )
    (tree / "src/target/target.c").write_text(
        "static struct target_type *target_types[] = {\n\t&mips_m4k_target,\n};\n",
        encoding="utf-8",
    )
    (tree / "src/flash/nor/Makefile.am").write_text(
        "NOR_DRIVERS = \\\n"
        "\t%D%/mdr.c \\\n"
        "\t%D%/mspm0.c \\\n"
        "\t$(NULL)\n",
        encoding="utf-8",
    )
    (tree / "src/flash/nor/driver.h").write_text(
        "extern const struct flash_driver mdr_flash;\n"
        "extern const struct flash_driver mrvlqspi_flash;\n",
        encoding="utf-8",
    )
    (tree / "src/flash/nor/drivers.c").write_text(
        "static const struct flash_driver * const flash_drivers[] = {\n"
        "\t&mdr_flash,\n\t&mrvlqspi_flash,\n};\n",
        encoding="utf-8",
    )

    overlay = Path(__file__).parents[1] / "openocd/overlay"
    install(tree, overlay)
    install(tree, overlay)

    assert (tree / "src/target/mchp_ri4_bridge.c").is_file()
    assert (tree / "src/target/mchp_ri4_bridge.h").is_file()
    assert (tree / "src/flash/nor/mchp_ri4.c").is_file()
    assert (tree / "tcl/interface/mchp-ri4.cfg").is_file()
    assert (tree / "tcl/target/mchp-ri4.cfg").is_file()
    assert (tree / "tcl/target/mchp-renode.cfg").is_file()
    makefile_text = (tree / "src/target/Makefile.am").read_text()
    assert makefile_text.count("mchp_ri4_bridge.c") == 1
    assert bridge_path in makefile_text
    assert "mchp_ri4_bridge.h" in makefile_text
    assert (tree / "src/flash/nor/Makefile.am").read_text().count("mchp_ri4.c") == 1
    assert (tree / "src/flash/nor/driver.h").read_text().count("mchp_ri4_flash") == 1
    assert (tree / "src/flash/nor/drivers.c").read_text().count("&mchp_ri4_flash") == 1
    assert (tree / "src/target/target_type.h").read_text().count("mchp_ri4_bridge_target") == 1
    assert (tree / "src/target/target.c").read_text().count("&mchp_ri4_bridge_target") == 1
