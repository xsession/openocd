from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from mchp_simulator.firmware_image import FirmwareImage, Segment

from .gdb_session import RenodeGdbSession, profile_for_core


_CORE_ARGS = {
    "pic16": ("PIC16", "PIC16", 0x200000),
    "pic18": ("PIC18", "PIC18", 0xA00000),
    "dspic30": ("dsPIC30F5011", "DSPIC30F", 0x1000),
    "dspic33": ("dsPIC33", "dsPIC33", 0x100),
}


def _firmware_hex_path(path: Path, temp_dir: Path) -> Path:
    if path.suffix.lower() in {".hex", ".ihex", ".elf"}:
        return path
    if path.suffix.lower() == ".bin":
        output = temp_dir / f"{path.stem}.hex"
        FirmwareImage(segments=(Segment(0, path.read_bytes()),)).to_intel_hex_path(str(output))
        return output
    raise ValueError("firmware must be .bin, .hex, .ihex, or .elf")


def validate(
    *,
    host: str,
    port: int,
    core: str,
    firmware: Optional[Path],
    timeout: float,
    run_seconds: float,
    breakpoint_address: int,
    watch_address: Optional[int],
) -> Dict[str, Any]:
    processor, family, default_watch = _CORE_ARGS[core]
    profile = profile_for_core(processor, family)
    report: Dict[str, Any] = {"core": core, "endpoint": f"{host}:{port}", "checks": []}

    session = RenodeGdbSession.open_gdb(
        host=host,
        port=port,
        processor=processor,
        family=family,
        timeout=timeout,
    )
    try:
        report["inventory"] = session.script_inventory()
        report["checks"].append({"name": "connect", "ok": True})

        session.enter_debug_mode()
        report["checks"].append({"name": "debug-enter", "ok": True})

        session.erase()
        report["checks"].append({"name": "erase", "ok": True, "bytes": profile.flash_size})

        with tempfile.TemporaryDirectory(prefix="mchp-renode-") as tmp:
            if firmware is not None:
                image_path = _firmware_hex_path(firmware, Path(tmp))
                programmed = session.program_hex(
                    str(image_path), erase_first=False, verify=True, chunk_size=512
                )
                report["checks"].append(
                    {
                        "name": "program-verify",
                        "ok": True,
                        "bytes": programmed["bytesProgrammed"],
                        "path": str(firmware),
                    }
                )

        session.set_pc(profile.reset_pc)
        pc_before = session.get_pc()["pc"]
        report["checks"].append({"name": "pc-read-write", "ok": pc_before == profile.reset_pc})

        bp = session.add_breakpoint(breakpoint_address, kind=2)
        session.remove_breakpoint(breakpoint_address, slot=bp["slot"])
        report["checks"].append({"name": "hardware-breakpoint", "ok": True})

        effective_watch = default_watch if watch_address is None else watch_address
        for access in ("read", "write", "access"):
            wp = session.add_watchpoint(effective_watch, length=1, access=access)
            session.remove_watchpoint(effective_watch, slot=wp["slot"])
        report["checks"].append(
            {"name": "watchpoints", "ok": True, "address": effective_watch}
        )

        stepped = session.step_target()
        report["checks"].append(
            {"name": "single-step", "ok": stepped["state"] == "halted", "pc": stepped["pc"]}
        )

        session.run_target()
        time.sleep(max(0.0, run_seconds))
        halted = session.halt_target()
        report["checks"].append(
            {
                "name": "run-halt",
                "ok": halted["state"] == "halted",
                "stopReply": halted.get("stopReply"),
            }
        )

        reset = session.reset_target()
        report["checks"].append(
            {"name": "reset", "ok": reset["state"] == "halted", "pc": reset["pc"]}
        )
        report["ok"] = all(check["ok"] for check in report["checks"])
        return report
    finally:
        session.close()


def _int_auto(value: str) -> int:
    return int(value, 0)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Microchip flash/debug operations against a running Renode GDB server"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3333)
    parser.add_argument("--core", choices=tuple(_CORE_ARGS), default="pic18")
    parser.add_argument("--firmware", type=Path)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--run-seconds", type=float, default=0.05)
    parser.add_argument("--breakpoint-address", type=_int_auto, default=0)
    parser.add_argument("--watch-address", type=_int_auto)
    args = parser.parse_args(argv)

    try:
        report = validate(
            host=args.host,
            port=args.port,
            core=args.core,
            firmware=args.firmware,
            timeout=args.timeout,
            run_seconds=args.run_seconds,
            breakpoint_address=args.breakpoint_address,
            watch_address=args.watch_address,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "core": args.core,
                    "endpoint": f"{args.host}:{args.port}",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
