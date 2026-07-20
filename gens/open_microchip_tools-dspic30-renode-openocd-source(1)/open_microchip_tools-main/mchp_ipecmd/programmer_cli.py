from __future__ import annotations

import argparse
import io
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, TextIO

from mchp_simulator.device_catalog import available_device_names


DEFAULT_TOOL = "PK4"


class ProgrammerCliError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProgramRequest:
    hex_path: Path
    device: str
    tool: str = DEFAULT_TOOL
    serial: str | None = None
    verify: bool = True
    power_target: bool = False
    release_from_reset: bool = True
    erase_first: bool = False
    extra_args: tuple[str, ...] = ()


def canonical_device_name(device: str, known_devices: Sequence[str] | None = None) -> str:
    cleaned = (device or "").strip()
    if not cleaned:
        raise ProgrammerCliError("A target PIC device is required.")

    devices = list(known_devices or available_device_names())
    if not devices:
        return cleaned.upper()

    lower_map = {name.lower(): name for name in devices}
    exact = lower_map.get(cleaned.lower())
    if exact:
        return exact

    suggestions = [name for name in devices if name.lower().startswith(cleaned.lower())][:8]
    suffix = f" Suggestions: {', '.join(suggestions)}" if suggestions else ""
    raise ProgrammerCliError(f"Unknown device '{device}'.{suffix}")


def build_ipecmd_command(request: ProgramRequest) -> list[str]:
    raise ProgrammerCliError(
        "Repo-only hardware programming is not implemented yet. "
        "The repo has RI4 transport primitives and simulator debug support, "
        "but not a complete native PICkit 4/ICD4 flash programming pipeline."
    )


def run_ipecmd(command: Sequence[str], *, stdout: TextIO, stderr: TextIO) -> int:
    raise ProgrammerCliError(
        "Repo-only hardware programming is not implemented yet."
    )


def _format_command(command: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return " ".join(shlex.quote(part) for part in command)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Program a PIC MCU from an Intel HEX file using MPLAB IPECMD and a PICkit 4.",
    )
    parser.add_argument("hex_file", nargs="?", help="Path to the Intel HEX file to program")
    parser.add_argument("--device", "-d", help="Target PIC device name, for example PIC16F1509")
    parser.add_argument("--tool", default=DEFAULT_TOOL, help="Programmer short name passed to IPECMD")
    parser.add_argument("--serial", help="Specific PICkit serial number to select")
    parser.add_argument(
        "--list-devices",
        nargs="?",
        const="",
        metavar="PREFIX",
        help="List known device names from the bundled MPLAB snapshot, optionally filtered by prefix",
    )
    parser.add_argument("--power-target", action="store_true", help="Power the target from the PICkit 4")
    parser.add_argument(
        "--hold-in-reset",
        dest="release_from_reset",
        action="store_false",
        help="Do not pass -OL; keep the target held in reset after programming",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip the post-program verify step",
    )
    parser.add_argument("--erase-first", action="store_true", help="Pass -OH to erase before programming")
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Append one raw IPECMD flag, for example --extra-arg=-OWT",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved IPECMD command without running it")
    parser.set_defaults(release_from_reset=True, verify=True)
    return parser


def _print_devices(prefix: str, *, stdout: TextIO) -> int:
    names = available_device_names()
    if prefix:
        names = [name for name in names if name.lower().startswith(prefix.lower())]
    for name in names:
        stdout.write(name + "\n")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    err = stderr or sys.stderr

    try:
        if args.list_devices is not None:
            return _print_devices(args.list_devices, stdout=out)

        if not args.hex_file:
            parser.error("the following arguments are required: hex_file")
        if not args.device:
            parser.error("the following arguments are required: --device/-d")

        hex_path = Path(args.hex_file).expanduser()
        if not hex_path.is_file():
            raise ProgrammerCliError(f"HEX file not found: {hex_path}")

        request = ProgramRequest(
            hex_path=hex_path.resolve(),
            device=canonical_device_name(args.device),
            tool=str(args.tool or DEFAULT_TOOL).strip().upper(),
            serial=(args.serial or "").strip() or None,
            verify=bool(args.verify),
            power_target=bool(args.power_target),
            release_from_reset=bool(args.release_from_reset),
            erase_first=bool(args.erase_first),
            extra_args=tuple(args.extra_arg),
        )
        command = build_ipecmd_command(request)

        if args.dry_run:
            out.write(_format_command(command) + "\n")
            return 0

        return run_ipecmd(command, stdout=out, stderr=err)
    except ProgrammerCliError as exc:
        err.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())