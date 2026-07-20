#!/usr/bin/env python3
"""Launch Renode, the Python bridge and an integrated OpenOCD for an E2E test."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mchp_simulator.firmware_image import FirmwareImage, Segment


CORE_CONFIG = {
    "pic16": {
        "processor": "PIC16",
        "family": "PIC16",
        "pc_bytes": 2,
        "watch": 0x200000,
        "image_bias": 0,
        "flash_size": 0x4000,
    },
    "pic18": {
        "processor": "PIC18",
        "family": "PIC18",
        "pc_bytes": 4,
        "watch": 0xA00000,
        "image_bias": 0,
        "flash_size": 0x20000,
    },
    "dspic30": {
        "processor": "dsPIC30F5011",
        "family": "DSPIC30F",
        "pc_bytes": 4,
        "watch": 0x1000,
        "image_bias": 0x100000,
        "flash_size": 0xAC00,
    },
    "dspic33": {
        "processor": "dsPIC33",
        "family": "dsPIC33",
        "pc_bytes": 4,
        "watch": 0x100,
        "image_bias": 0,
        "flash_size": 0x40000,
    },
}


def wait_port(host: str, port: int, timeout: float, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"process exited with code {process.returncode} before {host}:{port} opened")
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for {host}:{port}")


def as_hex_image(firmware: Path, temp_dir: Path) -> Path:
    suffix = firmware.suffix.lower()
    if suffix in {".hex", ".ihex"}:
        return firmware.resolve()
    if suffix == ".bin":
        output = temp_dir / f"{firmware.stem}.hex"
        FirmwareImage(segments=(Segment(0, firmware.read_bytes()),)).to_intel_hex_path(str(output))
        return output
    if suffix == ".elf":
        image = FirmwareImage.from_elf_path(str(firmware))
        output = temp_dir / f"{firmware.stem}.hex"
        image.to_intel_hex_path(str(output))
        return output
    raise ValueError("firmware must be .bin, .hex, .ihex, or .elf")


def openocd_image_offset(image_path: Path, *, image_bias: int, flash_size: int) -> int:
    """Return the OpenOCD image offset needed for a Harvard flash window."""
    if image_bias == 0:
        return 0
    image = FirmwareImage.from_path(str(image_path))
    if all(
        0 <= segment.address and segment.address + len(segment.data) <= flash_size
        for segment in image.segments
    ):
        return image_bias
    return 0


def image_command(command: str, image_path: Path, offset: int) -> str:
    suffix = f" 0x{offset:x}" if offset else ""
    return f"{command} {{{image_path.as_posix()}}}{suffix}"


def terminate(process: Optional[subprocess.Popen], *, stdin_command: Optional[str] = None) -> None:
    if process is None or process.poll() is not None:
        return
    if stdin_command and process.stdin is not None:
        try:
            process.stdin.write(stdin_command)
            process.stdin.flush()
            process.wait(timeout=3.0)
            return
        except Exception:
            pass
    process.terminate()
    try:
        process.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3.0)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renode", type=Path, required=True, help="custom-cores Renode executable")
    parser.add_argument("--openocd", type=Path, required=True, help="OpenOCD executable with overlay compiled in")
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--core", choices=tuple(CORE_CONFIG), default="pic18")
    parser.add_argument("--gdb-port", type=int, default=3333)
    parser.add_argument("--bridge-port", type=int, default=9123)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--log-dir", type=Path)
    args = parser.parse_args(argv)

    cfg = CORE_CONFIG[args.core]
    log_dir = (args.log_dir or Path.cwd() / "renode-openocd-logs").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    renode_log_path = log_dir / f"{args.core}-renode.log"
    bridge_log_path = log_dir / f"{args.core}-bridge.log"
    openocd_log_path = log_dir / f"{args.core}-openocd.log"

    renode_process: Optional[subprocess.Popen] = None
    bridge_process: Optional[subprocess.Popen] = None
    with tempfile.TemporaryDirectory(prefix="mchp-renode-e2e-") as tmp:
        temp_dir = Path(tmp)
        image_path = as_hex_image(args.firmware.resolve(), temp_dir)
        image_offset = openocd_image_offset(
            image_path,
            image_bias=cfg["image_bias"],
            flash_size=cfg["flash_size"],
        )
        platform = ROOT / "renode" / "platforms" / f"{args.core}_openocd.repl"
        resc = temp_dir / f"{args.core}_openocd.resc"
        resc.write_text(
            "using sysbus\n"
            f'mach create "{args.core}-openocd"\n'
            f"machine LoadPlatformDescription @{platform.resolve().as_posix()}\n"
            "cpu PC 0x000000\n"
            f"machine StartGdbServer {args.gdb_port}\n"
            f'log ">>> {args.core}: GDB server ready on {args.gdb_port} <<<"\n',
            encoding="utf-8",
        )

        try:
            renode_log = renode_log_path.open("w", encoding="utf-8")
            renode_process = subprocess.Popen(
                [str(args.renode), "--console", "--disable-gui"],
                stdin=subprocess.PIPE,
                stdout=renode_log,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(args.renode.resolve().parent),
            )
            assert renode_process.stdin is not None
            renode_process.stdin.write(f"include @{resc.resolve().as_posix()}\n")
            renode_process.stdin.flush()
            wait_port("127.0.0.1", args.gdb_port, args.startup_timeout, renode_process)

            bridge_log = bridge_log_path.open("w", encoding="utf-8")
            bridge_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "mchp_openocd.bridge_server",
                    "--backend",
                    "renode",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.bridge_port),
                    "--renode-host",
                    "127.0.0.1",
                    "--renode-port",
                    str(args.gdb_port),
                ],
                stdout=bridge_log,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(ROOT),
            )
            wait_port("127.0.0.1", args.bridge_port, args.startup_timeout, bridge_process)

            target = "mchp.cpu"
            commands = [
                "init",
                f"mchp_ri4 capabilities {target}",
                "halt",
                "flash info 0",
                "flash erase_sector 0 0 last",
                image_command("flash write_image", image_path, image_offset),
                image_command("verify_image", image_path, image_offset),
                "reg pc 0",
                "step",
                "mdb 0 8",
                "mwb 0x20 0x5a",
                "mdb 0x20 1",
                "bp 0 2 hw",
                "rbp 0",
                f"wp 0x{cfg['watch']:x} 1 w",
                "rwp all",
                "resume",
                "sleep 50",
                "halt",
                "reset halt",
                image_command("verify_image", image_path, image_offset),
                "shutdown",
            ]
            openocd_args = [
                str(args.openocd),
                "-s",
                str((ROOT / "openocd" / "overlay" / "tcl").resolve()),
                "-c",
                "set MCHP_RI4_HOST 127.0.0.1",
                "-c",
                f"set MCHP_RI4_PORT {args.bridge_port}",
                "-c",
                f"set MCHP_RENODE_PROCESSOR {cfg['processor']}",
                "-c",
                f"set MCHP_RENODE_FAMILY {cfg['family']}",
                "-c",
                f"set MCHP_RENODE_PC_BYTES {cfg['pc_bytes']}",
                "-f",
                "target/mchp-renode.cfg",
            ]
            for command in commands:
                openocd_args.extend(("-c", command))

            result = subprocess.run(
                openocd_args,
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120.0,
                check=False,
            )
            openocd_log_path.write_text(result.stdout, encoding="utf-8")
            summary = {
                "ok": result.returncode == 0,
                "core": args.core,
                "firmware": str(args.firmware.resolve()),
                "returnCode": result.returncode,
                "logs": {
                    "renode": str(renode_log_path),
                    "bridge": str(bridge_log_path),
                    "openocd": str(openocd_log_path),
                },
            }
            print(json.dumps(summary, indent=2))
            return 0 if summary["ok"] else 1
        finally:
            terminate(bridge_process)
            terminate(renode_process, stdin_command="quit\n")


if __name__ == "__main__":
    raise SystemExit(main())
