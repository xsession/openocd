#!/usr/bin/env python3
"""Apply XDS100v2/v3 support to an OpenOCD source checkout.

The source edit adds `ftdi initial_signal <name> <0|1|z>`. Initial signals are
applied after the layout's initial GPIO state is queued, but before the first
MPSSE flush and before JTAG chain examination. This is required for XDS100's
PWR_RST low-to-high latch-clearing edge.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from pathlib import Path

MARKER = "struct ftdi_initial_signal"

DECLARATION = r'''

struct ftdi_initial_signal {
	char *name;
	char value;
	struct ftdi_initial_signal *next;
};

static struct ftdi_initial_signal *ftdi_initial_signals;
'''

APPLY_BLOCK = r'''
	/*
	 * Some FTDI adapters need a GPIO transition after the MPSSE engine is
	 * open, but before the JTAG chain is examined. Commit the layout's base
	 * state first, then queue configured initial signals. This guarantees a
	 * physical edge rather than only two states in one unflushed command
	 * stream. The normal final initialization flush commits the new state.
	 */
	if (ftdi_initial_signals) {
		int retval = mpsse_flush(mpsse_ctx);
		if (retval != ERROR_OK) {
			LOG_ERROR("couldn't commit initial FTDI GPIO state");
			return retval;
		}
	}

	for (struct ftdi_initial_signal *initial = ftdi_initial_signals;
			initial; initial = initial->next) {
		struct signal *sig = find_signal_by_name(initial->name);
		if (!sig) {
			LOG_ERROR("initial FTDI signal '%s' is not defined", initial->name);
			return ERROR_JTAG_INIT_FAILED;
		}

		int retval = ftdi_set_signal(sig, initial->value);
		if (retval != ERROR_OK)
			return retval;
	}
'''

HANDLER = r'''COMMAND_HANDLER(ftdi_handle_initial_signal_command)
{
	if (CMD_ARGC != 2 || strlen(CMD_ARGV[1]) != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	char value = CMD_ARGV[1][0];
	if (value != '0' && value != '1' && value != 'z' && value != 'Z') {
		LOG_ERROR("unknown signal level '%s', use 0, 1 or z", CMD_ARGV[1]);
		return ERROR_COMMAND_SYNTAX_ERROR;
	}

	struct ftdi_initial_signal **entry = &ftdi_initial_signals;
	while (*entry && strcmp((*entry)->name, CMD_ARGV[0]) != 0)
		entry = &(*entry)->next;

	if (!*entry) {
		*entry = calloc(1, sizeof(**entry));
		if (!*entry)
			return ERROR_FAIL;

		(*entry)->name = strdup(CMD_ARGV[0]);
		if (!(*entry)->name) {
			free(*entry);
			*entry = NULL;
			return ERROR_FAIL;
		}
	}

	(*entry)->value = value;
	return ERROR_OK;
}

'''

REGISTRATION = r'''	{
		.name = "initial_signal",
		.handler = &ftdi_handle_initial_signal_command,
		.mode = COMMAND_CONFIG,
		.help = "set a layout-specific signal after adapter open "
			"and before JTAG examination",
		.usage = "name (1|0|z)",
	},
'''

FREE_BLOCK = r'''	struct ftdi_initial_signal *initial = ftdi_initial_signals;
	while (initial) {
		struct ftdi_initial_signal *next = initial->next;
		free(initial->name);
		free(initial);
		initial = next;
	}
	ftdi_initial_signals = NULL;

'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def patch_ftdi(text: str) -> str:
    if MARKER in text:
        return text

    text = replace_once(
        text,
        "static struct signal *signals;\n",
        "static struct signal *signals;" + DECLARATION,
        "signal declaration",
    )

    gpio_anchor = (
        "\tmpsse_set_data_bits_low_byte(mpsse_ctx, output & 0xff, direction & 0xff);\n"
        "\tmpsse_set_data_bits_high_byte(mpsse_ctx, output >> 8, direction >> 8);\n"
    )
    text = replace_once(text, gpio_anchor, gpio_anchor + APPLY_BLOCK, "initial GPIO write")

    text = replace_once(
        text,
        "COMMAND_HANDLER(ftdi_handle_get_signal_command)\n",
        HANDLER + "COMMAND_HANDLER(ftdi_handle_get_signal_command)\n",
        "get_signal handler",
    )

    registration_anchor = (
        "\t{\n"
        "\t\t.name = \"set_signal\",\n"
        "\t\t.handler = &ftdi_handle_set_signal_command,\n"
    )
    text = replace_once(
        text,
        registration_anchor,
        REGISTRATION + registration_anchor,
        "set_signal registration",
    )

    cleanup_anchors = [
        "\tfree(swd_cmd_queue);\n",
        "\tfree(ftdi_device_desc);\n",
    ]
    for cleanup_anchor in cleanup_anchors:
        if cleanup_anchor in text:
            text = replace_once(
                text,
                cleanup_anchor,
                FREE_BLOCK + cleanup_anchor,
                "FTDI quit cleanup",
            )
            break
    else:
        raise RuntimeError("expected an FTDI quit cleanup anchor")
    return text


def update_udev_file(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if 'idProduct}=="a6d1"' in text:
        return False
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if 'idProduct}=="a6d0"' in line:
            insertion = (
                "\n# XDS100v3\n"
                'ATTRS{idVendor}=="0403", ATTRS{idProduct}=="a6d1", '
                'MODE="660", GROUP="plugdev", TAG+="uaccess"\n'
            )
            lines.insert(index + 1, insertion)
            path.write_text("".join(lines), encoding="utf-8")
            return True
    return False


def copy_overlay(bundle: Path, root: Path, dry_run: bool) -> list[Path]:
    copied: list[Path] = []
    mapping = {
        bundle / "overlay/tcl/interface/ftdi/xds100v2.cfg": root / "tcl/interface/ftdi/xds100v2.cfg",
        bundle / "overlay/tcl/interface/ftdi/xds100v3.cfg": root / "tcl/interface/ftdi/xds100v3.cfg",
        bundle / "overlay/tcl/interface/ftdi/xds100.cfg": root / "tcl/interface/ftdi/xds100.cfg",
        bundle / "overlay/udev/99-openocd-xds100.rules": root / "udev/99-openocd-xds100.rules",
        bundle / "overlay/docs/usage/xds100.md": root / "docs/usage/xds100.md",
        bundle / "examples/program-xds100.cfg": root / "examples/program-xds100.cfg",
        bundle / "examples/c2000/tms320f28069-xds100v2.cfg": root / "examples/c2000/tms320f28069-xds100v2.cfg",
        bundle / "examples/c2000/tms320f28069-xds100v3.cfg": root / "examples/c2000/tms320f28069-xds100v3.cfg",
        bundle / "examples/c2000/tms320f280049-xds100v2.cfg": root / "examples/c2000/tms320f280049-xds100v2.cfg",
        bundle / "examples/c2000/tms320f280049-xds100v3.cfg": root / "examples/c2000/tms320f280049-xds100v3.cfg",
        bundle / "examples/c2000/tms320f28m35x-xds100v2.cfg": root / "examples/c2000/tms320f28m35x-xds100v2.cfg",
        bundle / "examples/c2000/tms320f28m35x-xds100v3.cfg": root / "examples/c2000/tms320f28m35x-xds100v3.cfg",
    }
    for source, destination in mapping.items():
        copied.append(destination)
        if dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="OpenOCD repository root")
    parser.add_argument("--check", action="store_true", help="verify support is already applied")
    parser.add_argument("--dry-run", action="store_true", help="show source diff without writing")
    args = parser.parse_args()

    root = args.root.resolve()
    bundle = Path(__file__).resolve().parents[1]
    ftdi_path = root / "src/jtag/drivers/ftdi.c"
    if not ftdi_path.is_file():
        print(f"error: not an OpenOCD checkout: {ftdi_path} is missing", file=sys.stderr)
        return 2

    original = ftdi_path.read_text(encoding="utf-8")
    if args.check:
        required = [
            MARKER,
            "ftdi_handle_initial_signal_command",
            '.name = "initial_signal"',
            "initial FTDI signal",
        ]
        missing = [item for item in required if item not in original]
        configs = [
            root / "tcl/interface/ftdi/xds100v2.cfg",
            root / "tcl/interface/ftdi/xds100v3.cfg",
        ]
        missing.extend(str(path) for path in configs if not path.is_file())
        if missing:
            print("XDS100 support check failed; missing:", file=sys.stderr)
            for item in missing:
                print(f"  {item}", file=sys.stderr)
            return 1
        print("XDS100v2/v3 source and configuration support is installed.")
        return 0

    try:
        patched = patch_ftdi(original)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Use patches/0001-ftdi-initial-signal.patch manually if this checkout has diverged.", file=sys.stderr)
        return 1

    if args.dry_run:
        sys.stdout.writelines(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                patched.splitlines(keepends=True),
                fromfile=str(ftdi_path),
                tofile=str(ftdi_path),
            )
        )
        for path in copy_overlay(bundle, root, dry_run=True):
            print(f"would install {path}", file=sys.stderr)
        return 0

    if patched != original:
        backup = ftdi_path.with_suffix(".c.xds100-backup")
        if not backup.exists():
            shutil.copy2(ftdi_path, backup)
        ftdi_path.write_text(patched, encoding="utf-8")
        print(f"patched {ftdi_path}")
    else:
        print(f"source support already present in {ftdi_path}")

    for path in copy_overlay(bundle, root, dry_run=False):
        print(f"installed {path}")

    for candidate in [
        root / "contrib/60-openocd.rules",
        root / "udev/60-openocd.rules",
        root / "udev/99-openocd-probes.rules",
    ]:
        if update_udev_file(candidate):
            print(f"added XDS100v3 USB permissions to {candidate}")

    print("Run ./bootstrap, configure with --enable-ftdi, build, then execute the included tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
