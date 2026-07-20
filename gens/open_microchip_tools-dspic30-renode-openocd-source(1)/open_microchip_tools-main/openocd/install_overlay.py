#!/usr/bin/env python3
"""Install the Microchip RI4 target overlay into an OpenOCD source tree.

The operation is idempotent. It copies the maintained target/Tcl files and
registers the target and NOR flash driver in OpenOCD's build and driver tables.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

TARGET_SYMBOL = "mchp_ri4_bridge_target"
SOURCE_NAME = "mchp_ri4_bridge.c"
FLASH_SOURCE_NAME = "mchp_ri4.c"
FLASH_SYMBOL = "mchp_ri4_flash"


class InstallError(RuntimeError):
    pass


def _insert_once(text: str, marker: str, insertion: str, *, before: bool = True) -> str:
    if insertion.strip() in text:
        return text
    pos = text.find(marker)
    if pos < 0:
        raise InstallError(f"Cannot find insertion marker: {marker!r}")
    if before:
        return text[:pos] + insertion + text[pos:]
    pos += len(marker)
    return text[:pos] + insertion + text[pos:]


def install(source_tree: Path, overlay: Path) -> list[Path]:
    source_tree = source_tree.resolve()
    overlay = overlay.resolve()
    required = [
        source_tree / "src/target/Makefile.am",
        source_tree / "src/target/target.c",
        source_tree / "src/target/target_type.h",
        source_tree / "src/flash/nor/Makefile.am",
        source_tree / "src/flash/nor/driver.h",
        source_tree / "src/flash/nor/drivers.c",
        overlay / "src/target/mchp_ri4_bridge.c",
        overlay / "src/target/mchp_ri4_bridge.h",
        overlay / "src/flash/nor/mchp_ri4.c",
        overlay / "tcl/interface/mchp-ri4.cfg",
        overlay / "tcl/target/mchp-ri4.cfg",
        overlay / "tcl/target/mchp-renode.cfg",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InstallError("Missing required files:\n  " + "\n  ".join(missing))

    copied: list[Path] = []
    for relative in (
        Path("src/target/mchp_ri4_bridge.c"),
        Path("src/target/mchp_ri4_bridge.h"),
        Path("src/flash/nor/mchp_ri4.c"),
        Path("tcl/interface/mchp-ri4.cfg"),
        Path("tcl/target/mchp-ri4.cfg"),
        Path("tcl/target/mchp-renode.cfg"),
    ):
        destination = source_tree / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / relative, destination)
        copied.append(destination)

    makefile = source_tree / "src/target/Makefile.am"
    text = makefile.read_text(encoding="utf-8")
    if SOURCE_NAME not in text or "mchp_ri4_bridge.h" not in text:
        # Current xsession/openocd and upstream OpenOCD keep Makefile.am in
        # src/target, therefore %D% already expands to src/target. An older
        # prototype fixture used an extra /target component; retain support.
        current_marker = "\t%D%/testee.c \\\n"
        legacy_marker = "\t%D%/target/testee.c \\\n"
        if current_marker in text:
            insertion = ""
            if SOURCE_NAME not in text:
                insertion += "\t%D%/mchp_ri4_bridge.c \\\n"
            if "mchp_ri4_bridge.h" not in text:
                insertion += "\t%D%/mchp_ri4_bridge.h \\\n"
            text = _insert_once(text, current_marker, insertion)
        elif legacy_marker in text:
            insertion = ""
            if SOURCE_NAME not in text:
                insertion += "\t%D%/target/mchp_ri4_bridge.c \\\n"
            if "mchp_ri4_bridge.h" not in text:
                insertion += "\t%D%/target/mchp_ri4_bridge.h \\\n"
            text = _insert_once(text, legacy_marker, insertion)
        else:
            marker = "noinst_LTLIBRARIES"
            if marker not in text:
                marker = "TARGET_CORE_SRC"
            additions = ""
            if SOURCE_NAME not in text:
                additions += "libtarget_la_SOURCES += %D%/mchp_ri4_bridge.c\n"
            if "mchp_ri4_bridge.h" not in text:
                additions += "libtarget_la_SOURCES += %D%/mchp_ri4_bridge.h\n"
            text = _insert_once(text, marker, additions + "\n")
        makefile.write_text(text, encoding="utf-8")

    flash_makefile = source_tree / "src/flash/nor/Makefile.am"
    text = flash_makefile.read_text(encoding="utf-8")
    if FLASH_SOURCE_NAME not in text:
        mdr_marker = "\t%D%/mdr.c \\\n"
        msp_marker = "\t%D%/mspm0.c \\\n"
        insertion = "\t%D%/mchp_ri4.c \\\n"
        if mdr_marker in text:
            text = _insert_once(text, mdr_marker, insertion, before=False)
        else:
            text = _insert_once(text, msp_marker, insertion, before=True)
        flash_makefile.write_text(text, encoding="utf-8")

    flash_driver_h = source_tree / "src/flash/nor/driver.h"
    text = flash_driver_h.read_text(encoding="utf-8")
    flash_declaration = f"extern const struct flash_driver {FLASH_SYMBOL};\n"
    if flash_declaration not in text:
        marker = "extern const struct flash_driver mrvlqspi_flash;"
        if marker not in text:
            marker = "extern const struct flash_driver msp432_flash;"
        text = _insert_once(text, marker, flash_declaration)
        flash_driver_h.write_text(text, encoding="utf-8")

    flash_drivers_c = source_tree / "src/flash/nor/drivers.c"
    text = flash_drivers_c.read_text(encoding="utf-8")
    flash_registration = f"\t&{FLASH_SYMBOL},\n"
    if flash_registration not in text:
        marker = "\t&mrvlqspi_flash,"
        if marker not in text:
            marker = "\t&msp432_flash,"
        text = _insert_once(text, marker, flash_registration)
        flash_drivers_c.write_text(text, encoding="utf-8")

    target_type_h = source_tree / "src/target/target_type.h"
    text = target_type_h.read_text(encoding="utf-8")
    declaration = f"extern struct target_type {TARGET_SYMBOL};\n"
    if declaration not in text:
        marker = "extern struct target_type mips_m4k_target;"
        if marker not in text:
            marker = "extern struct target_type testee_target;"
        text = _insert_once(text, marker, declaration)
        target_type_h.write_text(text, encoding="utf-8")

    target_c = source_tree / "src/target/target.c"
    text = target_c.read_text(encoding="utf-8")
    registration = f"\t&{TARGET_SYMBOL},\n"
    if registration not in text:
        marker = "\t&mips_m4k_target,"
        if marker not in text:
            marker = "\t&testee_target,"
        text = _insert_once(text, marker, registration)
        target_c.write_text(text, encoding="utf-8")

    return copied + [
        makefile,
        target_type_h,
        target_c,
        flash_makefile,
        flash_driver_h,
        flash_drivers_c,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("openocd_source", type=Path)
    parser.add_argument(
        "--overlay",
        type=Path,
        default=Path(__file__).resolve().parent / "overlay",
        help="overlay root (defaults to openocd/overlay next to this script)",
    )
    args = parser.parse_args()
    try:
        changed = install(args.openocd_source, args.overlay)
    except InstallError as exc:
        parser.error(str(exc))
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
