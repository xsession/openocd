#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Convenience wrapper for TI C28x targets through OpenOCD.

This tool does not translate the C28x CPU architecture into ARM or any other
GDB architecture.  OpenOCD already exposes a GDB Remote Serial Protocol server;
the client GDB must still understand the C28x register file and target XML.

The wrapper normalizes the practical differences discovered during hardware
bring-up:

* start a known C28x OpenOCD board preset or a user-supplied config file,
* keep the usual GDB/TCL/telnet ports stable,
* wait until the GDB server is ready,
* run a repeatable ICEPick discovery pass,
* provide a simple OpenOCD monitor command client, and
* generate a Cortex-Debug external-server launch template.
"""

from __future__ import annotations

import argparse
import binascii
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable


PRESETS = {
    "f28m35x-xds100v3": {
        "description": "TMS320F28M35x Concerto C28x through XDS100v3",
        "board": "board/ti/tms320f28m35x-xds100v3.cfg",
        "target_core": "c2000",
        "target_name": "F28M35x C28x",
        "executable": "${workspaceFolder}/build/c28x.out",
        "adapter": "xds100v3",
        "usb_vid": "0403",
        "usb_pid": "A6D1",
    },
    "f28m35x-dual-xds100v3": {
        "description": "TMS320F28M35x Concerto Cortex-M3 + C28x through XDS100v3",
        "board": "board/ti/tms320f28m35x-dual-core-xds100v3.cfg",
        "target_core": "c2000",
        "target_name": "F28M35x C28x",
        "executable": "${workspaceFolder}/build/c28x.out",
        "adapter": "xds100v3",
        "m3_gdb_port": "3333",
        "c28x_gdb_port": "3334",
        "usb_vid": "0403",
        "usb_pid": "A6D1",
    },
    "f28069-xds100v3": {
        "description": "TMS320F28069 C28x through XDS100v3",
        "board": "board/ti/tms320f28069-xds100v3.cfg",
        "target_core": "c2000",
        "target_name": "F28069 C28x",
        "executable": "${workspaceFolder}/build/f28069.out",
        "adapter": "xds100v3",
        "usb_vid": "0403",
        "usb_pid": "A6D1",
    },
    "f280049-xds100v3": {
        "description": "TMS320F280049 C28x through XDS100v3",
        "board": "board/ti/tms320f280049-xds100v3.cfg",
        "target_core": "c2000",
        "target_name": "F280049 C28x",
        "executable": "${workspaceFolder}/build/f280049.out",
        "adapter": "xds100v3",
        "usb_vid": "0403",
        "usb_pid": "A6D1",
    },
}
DEFAULT_PRESET = "f28m35x-xds100v3"
DEFAULT_GDB_PORT = 3333
DEFAULT_TCL_PORT = 6666
DEFAULT_TELNET_PORT = 4444
DEFAULT_M3_MONITOR_GDB_PORT = 3335
DEFAULT_C28X_MONITOR_GDB_PORT = 3336
TCL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
READY_MARKERS = (
    "Listening on port {port} for gdb connections",
    "starting gdb server on {port}",
)


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "tcl").is_dir() and (parent / "tools").is_dir():
            return parent
    raise RuntimeError("could not locate OpenOCD repository root")


def default_openocd(root: Path) -> str:
    packaged = root / "artifacts" / "windows" / "openocd-windows-x86_64" / "bin" / "openocd.exe"
    if packaged.exists():
        return str(packaged)
    found = shutil.which("openocd")
    if found:
        return found
    return str(packaged if os.name == "nt" else "openocd")


def preset(args: argparse.Namespace) -> dict[str, str]:
    return PRESETS[args.preset]


def board_config(args: argparse.Namespace) -> str:
    return args.board or preset(args)["board"]


def build_openocd_args(args: argparse.Namespace, *, one_shot: bool) -> list[str]:
    cmd = [
        args.openocd,
        "-s",
        args.scripts,
    ]
    for item in args.config_set or []:
        if "=" not in item:
            raise SystemExit(f"--set expects NAME=VALUE, got: {item}")
        name, value = item.split("=", 1)
        if not TCL_NAME_RE.match(name):
            raise SystemExit(f"--set variable name is not a safe Tcl identifier: {name}")
        cmd += ["-c", f"set {name} {value}"]
    cmd += [
        "-f",
        board_config(args),
        "-c",
        f"gdb port {args.gdb_port}",
        "-c",
        f"tcl port {args.tcl_port}",
        "-c",
        f"telnet port {args.telnet_port}",
    ]
    if args.adapter_speed:
        cmd += ["-c", f"adapter speed {args.adapter_speed}"]
    for command in args.openocd_command or []:
        cmd += ["-c", command]
    if one_shot:
        cmd += ["-c", "init", "-c", "targets", "-c", "poll", "-c", "shutdown"]
    return cmd


def print_command(cmd: Iterable[str]) -> None:
    print("OpenOCD command:")
    print("  " + subprocess.list2cmdline(list(cmd)))


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def windows_connected_usb_devices() -> list[str]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            ["pnputil", "/enum-devices", "/connected", "/ids"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return result.stdout.splitlines()


def print_windows_usb_status(selected: dict[str, str]) -> bool:
    vid = selected.get("usb_vid", "").upper()
    pid = selected.get("usb_pid", "").upper()
    if not vid or not pid:
        return True

    expected = f"VID_{vid}&PID_{pid}"
    lines = windows_connected_usb_devices()
    if not lines:
        print("USB inventory: unavailable through pnputil.")
        return True

    matched = [line.strip() for line in lines if expected in line.upper()]
    nearby = [
        line.strip()
        for line in lines
        if "VID_0403" in line.upper()
        or "FTDI" in line.upper()
        or "DIGILENT" in line.upper()
        or "XDS100" in line.upper()
    ]

    if matched:
        print(f"USB inventory: found expected adapter {expected}.")
        for line in matched[:6]:
            print(f"  {line}")
        return True

    print(f"USB inventory: expected adapter {expected} was not found.")
    if nearby:
        print("Nearby FTDI/Digilent USB devices:")
        for line in nearby[:12]:
            print(f"  {line}")
    print("Connect the XDS100 probe, or select a board/interface config that matches")
    print("the probe that is actually plugged in.")
    return False


def run_preflight(args: argparse.Namespace) -> int:
    selected = preset(args)
    board = board_config(args)
    checks = [
        ("OpenOCD executable", Path(args.openocd)),
        ("OpenOCD scripts", Path(args.scripts)),
        ("C28x board/config file", Path(args.scripts) / board),
    ]
    print(f"Preset: {args.preset} - {selected['description']}")
    if args.board:
        print(f"Board override: {args.board}")
    print()

    failed = False
    for label, path in checks:
        exists = path.exists()
        failed = failed or not exists
        print(f"{label}: {'OK' if exists else 'MISSING'} - {path}")

    if os.name == "nt":
        print()
        if selected.get("adapter") == "xds100v3" or "xds100v3" in board.lower():
            print("Windows XDS100v3 driver expectation:")
            print("  MI_00: WinUSB/libwdi for OpenOCD")
            print("  MI_01: TI/vendor driver for the auxiliary port")
            print("If OpenOCD works only as Administrator, keep using --elevate or fix")
            print("the Windows device access policy for the WinUSB interface.")
            print()
            failed = failed or not print_windows_usb_status(selected)

    print()
    print("C28x GDB expectation:")
    print("  The client GDB must understand architecture 'c28x'.")
    print("  arm-none-eabi-gdb is expected to fail on the C28x target XML/registers.")
    return 1 if failed else 0


def run_elevated_windows(cmd: list[str], wait: bool) -> int:
    if os.name != "nt":
        print("--elevate is only supported on Windows.", file=sys.stderr)
        return 2
    quoted = subprocess.list2cmdline(cmd)
    wait_arg = "-Wait" if wait else ""
    root = str(repo_root())
    invocation = " ".join(["&", ps_quote(cmd[0]), *(ps_quote(arg) for arg in cmd[1:])])
    elevated_command = f"Set-Location {ps_quote(root)}; {invocation}; exit $LASTEXITCODE"
    ps_args = "@(" + ",".join(json.dumps(arg) for arg in (
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        elevated_command,
    )) + ")"
    ps = (
        "$p = Start-Process -Verb RunAs -PassThru "
        f"{wait_arg} -FilePath powershell "
        f"-ArgumentList {ps_args}; "
        "if ($p -and $p.ExitCode -ne $null) { exit $p.ExitCode }"
    )
    print("Launching elevated OpenOCD:")
    print(f"  {quoted}")
    return subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])


def run_probe(args: argparse.Namespace) -> int:
    cmd = build_openocd_args(args, one_shot=True)
    print_command(cmd)
    if args.elevate:
        return run_elevated_windows(cmd, wait=True)
    return subprocess.call(cmd)


def run_discover(args: argparse.Namespace) -> int:
    commands = [
        "init",
        "scan_chain",
        "c2000_icepick_read_idcode",
        "c2000_icepick_read_code",
        "c2000_icepick_scan_sdtaps",
        "c2000_icepick_scan_tsttaps",
        "targets",
        "poll",
        "shutdown",
    ]
    cmd = build_openocd_args(args, one_shot=False)
    for command in commands:
        cmd += ["-c", command]
    print_command(cmd)
    if args.elevate:
        return run_elevated_windows(cmd, wait=True)
    return subprocess.call(cmd)


def wait_for_ready(process: subprocess.Popen[str], gdb_port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    markers = tuple(marker.format(port=gdb_port) for marker in READY_MARKERS)
    while time.time() < deadline:
        line = process.stdout.readline() if process.stdout else ""
        if line:
            print(line, end="")
            if any(marker in line for marker in markers):
                return True
        elif process.poll() is not None:
            return False
        else:
            time.sleep(0.05)
    return False


def run_server(args: argparse.Namespace) -> int:
    cmd = build_openocd_args(args, one_shot=False)
    print_command(cmd)
    if args.elevate:
        return run_elevated_windows(cmd, wait=False)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    ready = wait_for_ready(process, args.gdb_port, args.ready_timeout)
    if ready:
        print()
        print(f"OpenOCD GDB server ready on localhost:{args.gdb_port}")
        print(f"OpenOCD TCL monitor ready on localhost:{args.tcl_port}")
        print(f"OpenOCD telnet monitor ready on localhost:{args.telnet_port}")
    else:
        print()
        print("OpenOCD did not report GDB readiness before timeout.", file=sys.stderr)

    if args.wait_ready:
        return 0 if ready else 1

    try:
        while True:
            line = process.stdout.readline() if process.stdout else ""
            if line:
                print(line, end="")
            elif process.poll() is not None:
                return process.returncode
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        try:
            return process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            return process.wait(timeout=5)


def tcl_command(host: str, port: int, command: str, timeout: float) -> str:
    terminator = b"\x1a"
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(command.encode("utf-8") + terminator)
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if terminator in chunk:
                break
    data = b"".join(chunks)
    if terminator in data:
        data = data.split(terminator, 1)[0]
    return data.decode("utf-8", errors="replace")


def run_monitor(args: argparse.Namespace) -> int:
    status = 0
    for command in args.commands:
        try:
            output = tcl_command(args.host, args.tcl_port, command, args.socket_timeout)
            print(f"> {command}")
            if output.strip():
                print(output.rstrip())
        except OSError as exc:
            print(f"monitor command failed: {exc}", file=sys.stderr)
            status = 1
            break
    return status


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
    return "O" + binascii.hexlify(data.encode("utf-8", errors="replace")).decode("ascii")


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


class MonitorGdbProxy:
    """Minimal RSP server that only makes GDB/Cortex-Debug monitor commands safe.

    This is intentionally not a CPU-debug implementation. It advertises a tiny
    ARM-compatible register file so ordinary GDB clients can attach, then
    forwards qRcmd packets to OpenOCD's TCL monitor. Register reads return zero
    placeholders and memory/control packets fail closed.
    """

    def __init__(self, label: str, listen_host: str, listen_port: int,
                 tcl_host: str, tcl_port: int, socket_timeout: float) -> None:
        self.label = label
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.tcl_host = tcl_host
        self.tcl_port = tcl_port
        self.socket_timeout = socket_timeout
        self.stop_event = threading.Event()
        self.no_ack = False

    def serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.listen_host, self.listen_port))
            server.listen(4)
            server.settimeout(0.5)
            print(f"{self.label} monitor-only GDB proxy listening on {self.listen_host}:{self.listen_port}", flush=True)
            while not self.stop_event.is_set():
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                print(f"{self.label} monitor-only GDB client: {addr[0]}:{addr[1]}", flush=True)
                with client:
                    client.settimeout(self.socket_timeout)
                    self.handle_client(client)

    def stop(self) -> None:
        self.stop_event.set()

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
                self.send_packet(client, "S05")
                continue
            close = self.handle_payload(client, payload)
            if close:
                return

    def handle_payload(self, client: socket.socket, payload: str) -> bool:
        if payload.startswith("qSupported"):
            self.send_packet(client, "PacketSize=4000;QStartNoAckMode+;qXfer:features:read+")
        elif payload == "QStartNoAckMode":
            self.send_packet(client, "OK")
            self.no_ack = True
        elif payload.startswith("qXfer:features:read:target.xml:"):
            self.handle_target_xml(client, payload)
        elif payload.startswith("qRcmd,"):
            self.handle_monitor_command(client, payload.split(",", 1)[1])
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
        elif payload.startswith(("vCont", "c", "s")):
            self.send_packet(client, "S05")
        elif payload == "g":
            self.send_packet(client, "00000000" * 17)
        elif payload.startswith("p"):
            self.send_packet(client, "00000000")
        elif payload.startswith(("m", "M", "X")):
            self.send_packet(client, "E01")
        elif payload.startswith(("Z", "z")):
            self.send_packet(client, "E01")
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

    def handle_monitor_command(self, client: socket.socket, hex_command: str) -> None:
        command = rsp_decode_hex(hex_command).strip()
        if command.startswith("monitor "):
            command = command[len("monitor "):].strip()
        if not command:
            self.send_packet(client, "OK")
            return
        try:
            output = tcl_command(self.tcl_host, self.tcl_port, command, self.socket_timeout)
            text = f"[{self.label}] monitor {command}\n{output}"
            for start in range(0, len(text), 512):
                self.send_packet(client, rsp_encode_console(text[start:start + 512]))
            self.send_packet(client, "OK")
        except OSError as exc:
            self.send_packet(client, rsp_encode_console(f"[{self.label}] monitor failed: {exc}\n"))
            self.send_packet(client, "E01")


def run_gdb_monitor_proxy(args: argparse.Namespace) -> int:
    proxies = [
        MonitorGdbProxy("F28M35x M3", args.listen_host, args.m3_port,
                        args.tcl_host, args.tcl_port, args.socket_timeout),
        MonitorGdbProxy("F28M35x C28x", args.listen_host, args.c28x_port,
                        args.tcl_host, args.tcl_port, args.socket_timeout),
    ]
    threads = [threading.Thread(target=proxy.serve, daemon=True) for proxy in proxies]
    for thread in threads:
        thread.start()
    print("Use these only for monitor commands; they do not debug CPU execution.")
    try:
        while all(thread.is_alive() for thread in threads):
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        for proxy in proxies:
            proxy.stop()
    return 0


def run_cortex_debug_json(args: argparse.Namespace) -> int:
    selected = preset(args)
    gdb_port = int(selected.get("c28x_gdb_port", args.gdb_port))
    config = {
        "name": f"{selected['target_name']} via OpenOCD",
        "type": "cortex-debug",
        "request": "attach",
        "servertype": "external",
        "targetCore": selected["target_core"],
        "cwd": "${workspaceFolder}",
        "executable": args.executable or selected["executable"],
        "gdbPath": "C:/path/to/c28x-capable-gdb.exe",
        "gdbTarget": f"localhost:{gdb_port}",
        "overrideAttachCommands": [],
        "postAttachCommands": [
            'interpreter-exec console "monitor targets"',
            'interpreter-exec console "monitor poll"',
        ],
    }
    print(json.dumps(config, indent=2))
    print()
    print("Note: this template still requires a GDB that understands C28x.")
    return 0


def add_common_openocd_args(parser: argparse.ArgumentParser, root: Path) -> None:
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=sorted(PRESETS),
        help="known C28x board preset",
    )
    parser.add_argument("--openocd", default=default_openocd(root), help="OpenOCD executable")
    parser.add_argument("--scripts", default=str(root / "tcl"), help="OpenOCD script directory")
    parser.add_argument("--board", default="", help="OpenOCD board/target config override")
    parser.add_argument(
        "--set",
        dest="config_set",
        action="append",
        help="Tcl variable set before the board/config file is sourced, as NAME=VALUE",
    )
    parser.add_argument("--gdb-port", type=int, default=DEFAULT_GDB_PORT, help="GDB server port")
    parser.add_argument("--tcl-port", type=int, default=DEFAULT_TCL_PORT, help="OpenOCD TCL monitor port")
    parser.add_argument("--telnet-port", type=int, default=DEFAULT_TELNET_PORT, help="OpenOCD telnet port")
    parser.add_argument("--adapter-speed", type=int, default=1000, help="adapter speed in kHz")
    parser.add_argument(
        "-c",
        "--openocd-command",
        action="append",
        help="extra OpenOCD command passed with -c before init",
    )
    parser.add_argument("--elevate", action="store_true", help="launch OpenOCD via Windows UAC")


def parse_args(argv: list[str]) -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    preflight = sub.add_parser("preflight", help="check local wrapper prerequisites")
    add_common_openocd_args(preflight, root)
    preflight.set_defaults(func=run_preflight)

    probe = sub.add_parser("probe", help="run init/targets/poll/shutdown once")
    add_common_openocd_args(probe, root)
    probe.set_defaults(func=run_probe)

    discover = sub.add_parser("discover", help="run safe ICEPick/JTAG discovery once")
    add_common_openocd_args(discover, root)
    discover.set_defaults(func=run_discover)

    server = sub.add_parser("server", help="start OpenOCD and keep it running")
    add_common_openocd_args(server, root)
    server.add_argument("--ready-timeout", type=float, default=20.0, help="seconds to wait for GDB readiness")
    server.add_argument("--wait-ready", action="store_true", help="exit after readiness check")
    server.set_defaults(func=run_server)

    monitor = sub.add_parser("monitor", help="send commands through the OpenOCD TCL monitor")
    monitor.add_argument("commands", nargs="+", help="OpenOCD commands, for example: targets poll")
    monitor.add_argument("--host", default="localhost", help="OpenOCD host")
    monitor.add_argument("--tcl-port", type=int, default=DEFAULT_TCL_PORT, help="OpenOCD TCL monitor port")
    monitor.add_argument("--socket-timeout", type=float, default=5.0, help="socket timeout in seconds")
    monitor.set_defaults(func=run_monitor)

    proxy = sub.add_parser("gdb-monitor-proxy", help="serve monitor-only GDB/RSP proxies backed by OpenOCD TCL")
    proxy.add_argument("--listen-host", default="localhost", help="proxy bind host")
    proxy.add_argument("--m3-port", type=int, default=DEFAULT_M3_MONITOR_GDB_PORT, help="M3 monitor-only GDB port")
    proxy.add_argument("--c28x-port", type=int, default=DEFAULT_C28X_MONITOR_GDB_PORT, help="C28x monitor-only GDB port")
    proxy.add_argument("--tcl-host", default="localhost", help="OpenOCD TCL monitor host")
    proxy.add_argument("--tcl-port", type=int, default=DEFAULT_TCL_PORT, help="OpenOCD TCL monitor port")
    proxy.add_argument("--socket-timeout", type=float, default=5.0, help="socket timeout in seconds")
    proxy.set_defaults(func=run_gdb_monitor_proxy)

    cortex = sub.add_parser("cortex-debug-json", help="print Cortex-Debug external-server template")
    cortex.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=sorted(PRESETS),
        help="known C28x board preset",
    )
    cortex.add_argument("--executable", default="", help="firmware image/symbol file path for the template")
    cortex.add_argument("--gdb-port", type=int, default=DEFAULT_GDB_PORT, help="OpenOCD GDB server port")
    cortex.set_defaults(func=run_cortex_debug_json)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
