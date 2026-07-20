from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


class IntegrationError(RuntimeError):
    """Raised when an OpenOCD checkout does not match the supported layout."""


@dataclass(frozen=True)
class Edit:
    path: str
    anchor: str
    replacement: str


EDITS = (
    Edit(
        "src/target/Makefile.am",
        "\t%D%/testee.c \\\n",
        "\t%D%/testee.c \\\n\t%D%/mchp_ri4_bridge.c \\\n\t%D%/mchp_ri4_bridge.h \\\n",
    ),
    Edit(
        "src/target/target.c",
        "\t&mem_ap_target,\n\t&mips_m4k_target,",
        "\t&mem_ap_target,\n\t&mchp_ri4_bridge_target,\n\t&mips_m4k_target,",
    ),
    Edit(
        "src/target/target_type.h",
        "extern struct target_type mem_ap_target;\nextern struct target_type mips_m4k_target;",
        "extern struct target_type mem_ap_target;\nextern struct target_type mchp_ri4_bridge_target;\nextern struct target_type mips_m4k_target;",
    ),
    Edit(
        "src/flash/nor/Makefile.am",
        "\t%D%/mdr.c \\\n",
        "\t%D%/mdr.c \\\n\t%D%/mchp_ri4.c \\\n",
    ),
    Edit(
        "src/flash/nor/driver.h",
        "extern const struct flash_driver mdr_flash;\nextern const struct flash_driver mrvlqspi_flash;",
        "extern const struct flash_driver mdr_flash;\nextern const struct flash_driver mchp_ri4_flash;\nextern const struct flash_driver mrvlqspi_flash;",
    ),
    Edit(
        "src/flash/nor/drivers.c",
        "\t&mdr_flash,\n\t&mrvlqspi_flash,",
        "\t&mdr_flash,\n\t&mchp_ri4_flash,\n\t&mrvlqspi_flash,",
    ),
)

COPIES = (
    ("src/target/mchp_ri4_bridge.c", "src/target/mchp_ri4_bridge.c"),
    ("src/target/mchp_ri4_bridge.h", "src/target/mchp_ri4_bridge.h"),
    ("src/flash/nor/mchp_ri4.c", "src/flash/nor/mchp_ri4.c"),
    ("tcl/interface/mchp-ri4.cfg", "tcl/interface/mchp-ri4.cfg"),
    ("tcl/target/mchp-ri4.cfg", "tcl/target/mchp-ri4.cfg"),
    ("tcl/target/mchp-renode.cfg", "tcl/target/mchp-renode.cfg"),
)


def overlay_root() -> Path:
    return Path(__file__).resolve().parents[1] / "openocd" / "overlay"


def validate_checkout(root: Path) -> None:
    missing = [edit.path for edit in EDITS if not (root / edit.path).is_file()]
    if missing:
        raise IntegrationError(
            "Not a supported OpenOCD checkout; missing: " + ", ".join(sorted(missing))
        )


def integration_status(root: Path) -> dict[str, object]:
    validate_checkout(root)
    installed = []
    pending = []
    incompatible = []
    for edit in EDITS:
        text = (root / edit.path).read_text(encoding="utf-8")
        marker = edit.replacement.replace(edit.anchor, "", 1)
        if marker and marker in text:
            installed.append(edit.path)
        elif edit.anchor in text:
            pending.append(edit.path)
        else:
            incompatible.append(edit.path)
    copied = [destination for _, destination in COPIES if (root / destination).is_file()]
    return {
        "installedEdits": installed,
        "pendingEdits": pending,
        "incompatibleEdits": incompatible,
        "copiedFiles": copied,
        "ready": not incompatible,
        "installed": len(installed) == len(EDITS) and len(copied) == len(COPIES),
    }


def apply_integration(root: Path, *, dry_run: bool = False) -> list[str]:
    validate_checkout(root)
    changed: list[str] = []
    for edit in EDITS:
        destination = root / edit.path
        text = destination.read_text(encoding="utf-8")
        marker = edit.replacement.replace(edit.anchor, "", 1)
        if marker and marker in text:
            continue
        if edit.anchor not in text:
            raise IntegrationError(
                f"Cannot patch {edit.path}: expected anchor was not found. "
                "The OpenOCD source layout may have changed."
            )
        if not dry_run:
            destination.write_text(text.replace(edit.anchor, edit.replacement, 1), encoding="utf-8")
        changed.append(edit.path)

    source_root = overlay_root()
    for source_rel, destination_rel in COPIES:
        source = source_root / source_rel
        destination = root / destination_rel
        if destination.is_file() and destination.read_bytes() == source.read_bytes():
            continue
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        changed.append(destination_rel)
    return changed


def remove_integration(root: Path, *, dry_run: bool = False) -> list[str]:
    validate_checkout(root)
    changed: list[str] = []
    for edit in reversed(EDITS):
        destination = root / edit.path
        text = destination.read_text(encoding="utf-8")
        marker = edit.replacement.replace(edit.anchor, "", 1)
        if not marker or marker not in text:
            continue
        if edit.replacement not in text:
            raise IntegrationError(
                f"Cannot safely remove integration from {edit.path}; the edited block changed."
            )
        if not dry_run:
            destination.write_text(text.replace(edit.replacement, edit.anchor, 1), encoding="utf-8")
        changed.append(edit.path)

    for _, destination_rel in COPIES:
        destination = root / destination_rel
        if destination.exists():
            if not dry_run:
                destination.unlink()
            changed.append(destination_rel)
    return changed


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the Microchip RI4 bridge target into an OpenOCD source checkout"
    )
    parser.add_argument("checkout", type=Path, help="path to the OpenOCD source checkout")
    parser.add_argument("--check", action="store_true", help="only report compatibility/status")
    parser.add_argument("--remove", action="store_true", help="remove files and deterministic edits")
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing")
    args = parser.parse_args(argv)
    root = args.checkout.resolve()

    try:
        if args.check:
            status = integration_status(root)
            for key, value in status.items():
                print(f"{key}: {value}")
            return 0 if status["ready"] else 2
        changed = (
            remove_integration(root, dry_run=args.dry_run)
            if args.remove
            else apply_integration(root, dry_run=args.dry_run)
        )
    except IntegrationError as exc:
        parser.error(str(exc))
    _print_lines(changed or ["No changes required."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
