#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""GDB/RSP facade for Microchip MPLAB X MDB.

MDB is a command-line debugger, not a GDB remote server. This wrapper exposes a
small GDB Remote Serial Protocol endpoint so GDB-fronted tools such as
Cortex-Debug can connect through ``servertype: external`` and send
``monitor ...`` commands that are executed by MDB command files.

The wrapper intentionally starts in a monitor-safe mode. It does not claim to
turn MDB into a full source-level GDB server for every Microchip architecture.
It provides a normal-looking attach target, console output forwarding, and
optional translations for simple run/step/halt/break operations.
"""

from __future__ import annotations

import argparse
import binascii
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


DEFAULT_MDB = r"C:\Program Files\Microchip\MPLABX\v6.25\mplab_platform\bin\mdb.bat"
DEFAULT_GDB_PORT = 3340
DEFAULT_HOST = "127.0.0.1"
DEFAULT_TIMEOUT = 60.0
MAX_CONSOLE_TEXT = 1800
SAFE_COMMAND_RE = re.compile(r"^[\w .:/\\,+\-*=<>()\[\]$@#]+$")


TARGET_XML = """<?xml version="1.0"?>
<!DOCTYPE target SYSTEM "gdb-target.dtd">
<target>
  <architecture>arm</architecture>
  <feature name="org.gnu.gdb.arm.m-profile">
    <reg name="r0" bitsize="32" regnum="0" type="uint32"/>
    <reg name="r1" bitsize="32" regnum="1" type="uint32"/>
    <reg name="r2" bitsize="32" regnum="2" type="uint32"/>
    <reg name="r3" bitsize="32" regnum="3" type="uint32"/>
    <reg name="r4" bitsize="32" regnum="4" type="uint32"/>
    <reg name="r5" bitsize="32" regnum="5" type="uint32"/>
    <reg name="r6" bitsize="32" regnum="6" type="uint32"/>
    <reg name="r7" bitsize="32" regnum="7" type="uint32"/>
    <reg name="r8" bitsize="32" regnum="8" type="uint32"/>
    <reg name="r9" bitsize="32" regnum="9" type="uint32"/>
    <reg name="r10" bitsize="32" regnum="10" type="uint32"/>
    <reg name="r11" bitsize="32" regnum="11" type="uint32"/>
    <reg name="r12" bitsize="32" regnum="12" type="uint32"/>
    <reg name="sp" bitsize="32" regnum="13" type="data_ptr"/>
    <reg name="lr" bitsize="32" regnum="14" type="uint32"/>
    <reg name="pc" bitsize="32" regnum="15" type="code_ptr"/>
    <reg name="xpsr" bitsize="32" regnum="16" type="uint32"/>
  </feature>
</target>
"""


def rsp_checksum(payload: str) -> str:
    return f"{sum(payload.encode('ascii')) % 256:02x}"


def rsp_packet(payload: str) -> bytes:
    return f"${payload}#{rsp_checksum(payload)}".encode("ascii")


def rsp_decode_hex(data: str) -> str:
    if not data:
        return ""
    try:
        return binascii.unhexlify(data.encode("ascii")).decode("utf-8", errors="replace")
    except (binascii.Error, ValueError):
        return ""


def rsp_encode_console(data: str) -> str:
    return "O" + binascii.hexlify(data.encode("ascii", errors="replace")).decode("ascii")


def clean_mdb_output(output: str) -> str:
    lines = []
    skip_next = False
    for line in output.splitlines():
        if " DE org.jline.utils.Log " in line or " DE com.microchip." in line or " DE org.openide." in line:
            skip_next = True
            continue
        if " DE org.openide." in line:
            skip_next = True
            continue
        if line.startswith("SLF4J:"):
            continue
        if skip_next and "Unable to create a system terminal" in line:
            skip_next = False
            continue
        if skip_next and line.startswith(("INFO:", "WARNING:", "SEVERE:")):
            skip_next = False
            continue
        skip_next = False
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def ensure_safe_mdb_command(command: str) -> None:
    if not command or "\n" in command or "\r" in command:
        raise ValueError("MDB command must be one non-empty line")
    if not SAFE_COMMAND_RE.match(command):
        raise ValueError(f"MDB command contains unsupported characters: {command!r}")


class MdbRunner:
    def __init__(self, mdb: Path, *, device: str = "", hwtool: str = "",
                 image: str = "", log_dir: Path | None = None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.mdb = mdb
        self.device = device
        self.hwtool = hwtool
        self.image = image
        self.log_dir = log_dir
        self.timeout = timeout

    def preamble(self) -> list[str]:
        commands: list[str] = []
        if self.device:
            commands.append(f"Device {self.device}")
        if self.hwtool:
            commands.append(f"Hwtool {self.hwtool}")
        if self.image:
            commands.append(f"Program {self.image}")
        return commands

    def run_commands(self, commands: list[str]) -> tuple[int, str]:
        for command in commands:
            ensure_safe_mdb_command(command)
        with tempfile.TemporaryDirectory(prefix="openocd-mdb-") as temp:
            script = Path(temp) / "mdb-commands.txt"
            script.write_text("\n".join([*self.preamble(), *commands, "quit", ""]) , encoding="ascii")
            cmd = [str(self.mdb)]
            if self.log_dir:
                cmd += ["--log-dir", str(self.log_dir)]
            cmd.append(str(script))
            result = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout,
            )
        return result.returncode, result.stdout


class MdbGdbServer:
    def __init__(self, runner: MdbRunner, host: str, port: int,
                 *, enable_control: bool = False,
                 socket_timeout: float = 5.0) -> None:
        self.runner = runner
        self.host = host
        self.port = port
        self.enable_control = enable_control
        self.socket_timeout = socket_timeout
        self.stop_event = threading.Event()
        self.no_ack = False
        self.breakpoints: dict[str, int] = {}

    def serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(4)
            server.settimeout(0.5)
            print(f"MDB GDB facade listening on {self.host}:{self.port}", flush=True)
            while not self.stop_event.is_set():
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                print(f"MDB GDB client: {addr[0]}:{addr[1]}", flush=True)
                with client:
                    client.settimeout(self.socket_timeout)
                    self.handle_client(client)

    def read_packet(self, client: socket.socket) -> str | None:
        while True:
            ch = client.recv(1)
            if not ch:
                return None
            if ch == b"\x03":
                return "\x03"
            if ch == b"$":
                break
        payload = bytearray()
        while True:
            ch = client.recv(1)
            if not ch:
                return None
            if ch == b"#":
                break
            payload.extend(ch)
        checksum = client.recv(2)
        if len(checksum) != 2:
            return None
        if not self.no_ack:
            client.sendall(b"+")
        return payload.decode("ascii", errors="replace")

    def send_packet(self, client: socket.socket, payload: str) -> None:
        client.sendall(rsp_packet(payload))

    def handle_client(self, client: socket.socket) -> None:
        while not self.stop_event.is_set():
            try:
                payload = self.read_packet(client)
            except OSError:
                return
            if payload is None:
                return
            if payload == "\x03":
                self.run_mdb_console(client, ["Halt"])
                self.send_packet(client, "S05")
                continue
            if self.handle_payload(client, payload):
                return

    def handle_payload(self, client: socket.socket, payload: str) -> bool:
        if payload.startswith("qSupported"):
            self.send_packet(client, "PacketSize=4000;qXfer:features:read+")
        elif payload == "QStartNoAckMode":
            self.send_packet(client, "OK")
            self.no_ack = True
        elif payload.startswith("qXfer:features:read:target.xml:"):
            self.handle_target_xml(client, payload)
        elif payload.startswith("qRcmd,"):
            self.handle_monitor(client, payload.split(",", 1)[1])
        elif payload in {"?", "vStopped"}:
            self.send_packet(client, "S05")
        elif payload in {"qAttached", "qSymbol::"}:
            self.send_packet(client, "1" if payload == "qAttached" else "OK")
        elif payload in {"qC", "qfThreadInfo", "qsThreadInfo"}:
            self.send_packet(client, "QC1" if payload == "qC" else ("m1" if payload == "qfThreadInfo" else "l"))
        elif payload.startswith(("H", "T", "QNonStop", "QThreadEvents", "QListThreadsInStopReply")):
            self.send_packet(client, "OK")
        elif payload.startswith("vCont?"):
            self.send_packet(client, "vCont;c;s")
        elif payload.startswith(("vCont;c", "c")):
            self.handle_control(client, ["Continue"])
            self.send_packet(client, "S05")
        elif payload.startswith(("vCont;s", "s")):
            self.handle_control(client, ["Stepi 1"])
            self.send_packet(client, "S05")
        elif payload == "g":
            self.send_packet(client, "00000000" * 17)
        elif payload.startswith("p"):
            self.send_packet(client, "00000000")
        elif payload.startswith("m"):
            self.handle_memory_read(client, payload)
        elif payload.startswith(("M", "X")):
            self.send_packet(client, "E01")
        elif payload.startswith("Z0,"):
            self.handle_breakpoint(client, payload, insert=True)
        elif payload.startswith("z0,"):
            self.handle_breakpoint(client, payload, insert=False)
        elif payload.startswith(("Z", "z")):
            self.send_packet(client, "")
        elif payload in {"D", "k"}:
            self.send_packet(client, "OK")
            return True
        else:
            self.send_packet(client, "")
        return False

    def handle_target_xml(self, client: socket.socket, payload: str) -> None:
        try:
            _, request = payload.rsplit(":", 1)
            offset_text, length_text = request.split(",", 1)
            offset = int(offset_text, 16)
            length = int(length_text, 16)
        except ValueError:
            self.send_packet(client, "E01")
            return
        chunk = TARGET_XML[offset:offset + length]
        prefix = "l" if offset + length >= len(TARGET_XML) else "m"
        self.send_packet(client, prefix + chunk)

    def handle_memory_read(self, client: socket.socket, payload: str) -> None:
        try:
            _addr, length_text = payload[1:].split(",", 1)
            length = int(length_text, 16)
        except ValueError:
            self.send_packet(client, "E01")
            return
        self.send_packet(client, "00" * length)

    def handle_monitor(self, client: socket.socket, hex_command: str) -> None:
        command = rsp_decode_hex(hex_command).strip()
        if command.startswith("monitor "):
            command = command[len("monitor "):].strip()
        command = self.expand_monitor_alias(command)
        if not command:
            self.send_packet(client, "OK")
            return
        try:
            self.run_mdb_console(client, [command])
            self.send_packet(client, "OK")
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self.send_packet(client, rsp_encode_console(f"MDB command failed: {exc}\n"))
            self.send_packet(client, "OK")

    def expand_monitor_alias(self, command: str) -> str:
        aliases = {
            "discover": "Hwtool",
            "tools": "Hwtool",
            "supported": "Hwtool supported",
        }
        return aliases.get(command.lower(), command)

    def handle_control(self, client: socket.socket, commands: list[str]) -> None:
        if not self.enable_control:
            return
        try:
            self.run_mdb_console(client, commands)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self.send_packet(client, rsp_encode_console(f"MDB control command failed: {exc}\n"))

    def handle_breakpoint(self, client: socket.socket, payload: str, *, insert: bool) -> None:
        if not self.enable_control:
            self.send_packet(client, "OK")
            return
        try:
            _, addr, _kind = payload.split(",", 2)
            address = "0x" + addr
            if insert:
                code, output = self.runner.run_commands([f"break *{address}"])
                self.breakpoints[address] = self.breakpoints.get(address, len(self.breakpoints) + 1)
            else:
                number = self.breakpoints.pop(address, 0)
                command = f"delete {number}" if number else "delete"
                code, output = self.runner.run_commands([command])
            if output.strip():
                self.send_packet(client, rsp_encode_console(output))
            self.send_packet(client, "OK" if code == 0 else "E01")
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self.send_packet(client, rsp_encode_console(f"MDB breakpoint command failed: {exc}\n"))
            self.send_packet(client, "E01")

    def run_mdb_console(self, client: socket.socket, commands: list[str]) -> None:
        code, output = self.runner.run_commands(commands)
        output = clean_mdb_output(output)
        if output.strip():
            if len(output) > MAX_CONSOLE_TEXT:
                output = output[:MAX_CONSOLE_TEXT] + "\n[MDB facade output truncated]\n"
            self.send_packet(client, rsp_encode_console(output))
        if code != 0:
            raise subprocess.CalledProcessError(code, str(self.runner.mdb), output=output)


def run_preflight(args: argparse.Namespace) -> int:
    mdb = Path(args.mdb)
    print(f"MDB executable: {'OK' if mdb.exists() else 'MISSING'} - {mdb}")
    if not mdb.exists():
        return 1
    code, output = MdbRunner(mdb, timeout=args.timeout).run_commands(["help"])
    print(clean_mdb_output(output).rstrip())
    return code


def run_discover(args: argparse.Namespace) -> int:
    runner = MdbRunner(Path(args.mdb), timeout=args.timeout)
    commands = ["Hwtool"]
    if args.supported:
        commands.append("Hwtool supported")
    code, output = runner.run_commands(commands)
    print(clean_mdb_output(output).rstrip())
    print()
    print("MDB target note:")
    print("  MDB lists connected programmers without a device.")
    print("  MDB requires an explicit Device <part> before it can open a tool")
    print("  and communicate with the controller on the target board.")
    return code


def run_command(args: argparse.Namespace) -> int:
    runner = MdbRunner(
        Path(args.mdb),
        device=args.device,
        hwtool=args.hwtool,
        image=args.image,
        log_dir=Path(args.log_dir) if args.log_dir else None,
        timeout=args.timeout,
    )
    code, output = runner.run_commands(args.commands)
    print(clean_mdb_output(output).rstrip())
    return code


def run_server(args: argparse.Namespace) -> int:
    runner = MdbRunner(
        Path(args.mdb),
        device=args.device,
        hwtool=args.hwtool,
        image=args.image,
        log_dir=Path(args.log_dir) if args.log_dir else None,
        timeout=args.timeout,
    )
    server = MdbGdbServer(
        runner,
        args.listen_host,
        args.port,
        enable_control=args.enable_control,
        socket_timeout=args.socket_timeout,
    )
    print("Use monitor commands for MDB. Source-level behavior is limited by the selected MDB tool/device.", flush=True)
    try:
        server.serve()
    except KeyboardInterrupt:
        return 130
    return 0


def print_cortex_debug_json(args: argparse.Namespace) -> int:
    config = {
        "name": "Microchip MDB facade",
        "type": "cortex-debug",
        "request": "attach",
        "servertype": "external",
        "cwd": "${workspaceFolder}",
        "executable": args.executable or "${workspaceFolder}/build/firmware.elf",
        "gdbPath": args.gdb_path,
        "gdbTarget": f"{args.listen_host}:{args.port}",
        "overrideAttachCommands": [
            f"target-select extended-remote {args.listen_host}:{args.port}",
            "interpreter-exec console \"monitor help\"",
        ],
        "showDevDebugOutput": "raw",
    }
    print(__import__("json").dumps(config, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mdb", default=DEFAULT_MDB, help="path to Microchip mdb.bat or mdb.sh")
    sub = parser.add_subparsers(dest="action", required=True)

    preflight = sub.add_parser("preflight", help="verify MDB is present and responds")
    preflight.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    preflight.set_defaults(func=run_preflight)

    discover = sub.add_parser("discover", help="list connected MDB programmers")
    discover.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    discover.add_argument("--supported", action="store_true", help="also list supported MDB tool types")
    discover.set_defaults(func=run_discover)

    command = sub.add_parser("command", help="run one MDB command-file transaction")
    command.add_argument("commands", nargs="+", help="MDB commands, for example: 'Device PIC32MX...' 'Hwtool PICkit4'")
    command.add_argument("--device", default="", help="MDB Device name")
    command.add_argument("--hwtool", default="", help="MDB Hwtool selector, for example: PICkit4 or ICD4")
    command.add_argument("--image", default="", help="optional image passed through MDB Program before commands")
    command.add_argument("--log-dir", default="", help="optional MDB log directory")
    command.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    command.set_defaults(func=run_command)

    server = sub.add_parser("server", help="serve a GDB/RSP facade backed by MDB command files")
    server.add_argument("--listen-host", default=DEFAULT_HOST)
    server.add_argument("--port", type=int, default=DEFAULT_GDB_PORT)
    server.add_argument("--device", default="", help="MDB Device name")
    server.add_argument("--hwtool", default="", help="MDB Hwtool selector, for example: PICkit4 or ICD4")
    server.add_argument("--image", default="", help="optional image passed through MDB Program before commands")
    server.add_argument("--log-dir", default="", help="optional MDB log directory")
    server.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="MDB command timeout")
    server.add_argument("--socket-timeout", type=float, default=5.0)
    server.add_argument("--enable-control", action="store_true", help="translate continue/step/break packets to MDB")
    server.set_defaults(func=run_server)

    template = sub.add_parser("cortex-debug-json", help="print a Cortex-Debug external attach template")
    template.add_argument("--listen-host", default=DEFAULT_HOST)
    template.add_argument("--port", type=int, default=DEFAULT_GDB_PORT)
    template.add_argument("--gdb-path", default="arm-none-eabi-gdb")
    template.add_argument("--executable", default="")
    template.set_defaults(func=print_cortex_debug_json)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
