from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Union

from .rsp import (
    RspChecksumError,
    RspProtocolError,
    RspStreamParser,
    ascii_payload,
    encode_packet,
    hex_to_bytes,
    iter_kv_semi,
)


@dataclass(frozen=True)
class StopReply:
    raw: str
    kind: str
    signal: Optional[int] = None


class GdbRemoteClient:
    """Small, thread-aware GDB Remote Serial Protocol client.

    Normal commands are serialized. ``interrupt()`` intentionally bypasses the
    command lock so another thread can stop a target while ``continue_exec()``
    is waiting for a stop reply.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3333,
        timeout: float = 3.0,
        try_no_ack: bool = True,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.try_no_ack = try_no_ack

        self._sock: Optional[socket.socket] = None
        self._parser = RspStreamParser()
        self._no_ack = False
        self._command_lock = threading.RLock()
        self._send_lock = threading.Lock()

    def connect(self) -> Dict[str, str]:
        with self._command_lock:
            if self._sock is not None:
                return {}
            s = socket.create_connection((self.host, self.port), timeout=self.timeout)
            s.settimeout(self.timeout)
            self._sock = s

            supported = self.qSupported()
            if self.try_no_ack and supported.get("QStartNoAckMode") == "+":
                if self._send_and_expect_ok("QStartNoAckMode"):
                    self._no_ack = True
            return supported

    def close(self) -> None:
        with self._send_lock:
            sock = self._sock
            self._sock = None
            self._no_ack = False
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()

    def __enter__(self) -> "GdbRemoteClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def interrupt(self) -> None:
        """Send an asynchronous GDB interrupt (Ctrl-C)."""
        self._require_sock()
        with self._send_lock:
            self._require_sock()
            self._sock.sendall(b"\x03")

    def qSupported(self) -> Dict[str, str]:
        reply = self.send_command("qSupported")
        text = reply.decode("ascii", errors="replace")
        out: Dict[str, str] = {}
        for part in iter_kv_semi(text):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k] = v
            elif part.endswith("+") or part.endswith("-"):
                out[part[:-1]] = part[-1]
            else:
                out[part] = ""
        return out

    def query_stop(self) -> StopReply:
        return self._parse_stop_reply(self.send_command("?"))

    def read_register(self, register: int) -> bytes:
        if register < 0:
            raise ValueError("register must be non-negative")
        reply = self.send_command(f"p{register:x}")
        text = reply.decode("ascii", errors="replace")
        if text.startswith("E"):
            raise RuntimeError(f"RSP register read failed: {text}")
        return hex_to_bytes(text)

    def write_register(self, register: int, data: bytes) -> None:
        if register < 0:
            raise ValueError("register must be non-negative")
        if not data:
            raise ValueError("register data must not be empty")
        if not self._send_and_expect_ok(f"P{register:x}={data.hex()}"):
            raise RuntimeError(f"RSP register write failed for register {register}")

    def read_memory(self, addr: int, length: int) -> bytes:
        if addr < 0 or length < 0:
            raise ValueError("address and length must be non-negative")
        if length == 0:
            return b""
        payload = f"m{addr:x},{length:x}".encode("ascii")
        reply = self.send_command(payload)
        text = reply.decode("ascii", errors="replace")
        if text.startswith("E"):
            raise RuntimeError(f"RSP memory read failed: {text}")
        data = hex_to_bytes(text)
        if len(data) != length:
            raise RuntimeError(f"RSP memory read returned {len(data)} bytes; expected {length}")
        return data

    def write_memory(self, addr: int, data: bytes) -> None:
        if addr < 0:
            raise ValueError("address must be non-negative")
        if not data:
            return
        payload = f"M{addr:x},{len(data):x}:{data.hex()}".encode("ascii")
        if not self._send_and_expect_ok(payload):
            raise RuntimeError("RSP memory write failed")

    def continue_exec(self, addr: Optional[int] = None) -> StopReply:
        payload = f"c{addr:x}".encode("ascii") if addr is not None else b"c"
        # A continue operation is expected to wait until a breakpoint, watchpoint,
        # fault or asynchronous interrupt stops the target.
        reply = self.send_command(payload, response_timeout=None)
        return self._parse_stop_reply(reply)

    def step(self, addr: Optional[int] = None) -> StopReply:
        payload = f"s{addr:x}".encode("ascii") if addr is not None else b"s"
        # Unlike continue, a single-step is expected to complete promptly.
        # Preserve the configured timeout so an unresponsive emulator cannot
        # hang OpenOCD's request thread forever.
        reply = self.send_command(payload)
        return self._parse_stop_reply(reply)

    def remote_command(self, command: str) -> str:
        """Execute a GDB ``monitor`` command through qRcmd.

        RSP servers may emit any number of ``O`` console-output packets before
        the final ``OK`` packet. The decoded console text is returned.
        """
        payload = f"qRcmd,{command.encode('utf-8').hex()}".encode("ascii")
        output = bytearray()
        with self._command_lock:
            self._send_packet(payload)
            while True:
                reply = self._recv_packet(timeout=self.timeout)
                if reply == b"OK":
                    return output.decode("utf-8", errors="replace")
                if reply.startswith(b"E"):
                    raise RuntimeError(f"RSP monitor command failed: {reply.decode('ascii', errors='replace')}")
                if reply.startswith(b"O"):
                    try:
                        output.extend(hex_to_bytes(reply[1:].decode("ascii")))
                    except ValueError:
                        output.extend(reply[1:])
                    continue
                # Some servers return command output directly without O framing.
                output.extend(reply)
                return output.decode("utf-8", errors="replace")

    def set_sw_breakpoint(self, addr: int, kind: int = 2) -> bool:
        return self.insert_breakpoint(0, addr, kind)

    def clear_sw_breakpoint(self, addr: int, kind: int = 2) -> bool:
        return self.remove_breakpoint(0, addr, kind)

    def set_hw_breakpoint(self, addr: int, kind: int = 2) -> bool:
        return self.insert_breakpoint(1, addr, kind)

    def clear_hw_breakpoint(self, addr: int, kind: int = 2) -> bool:
        return self.remove_breakpoint(1, addr, kind)

    def set_write_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.insert_breakpoint(2, addr, length)

    def clear_write_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.remove_breakpoint(2, addr, length)

    def set_read_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.insert_breakpoint(3, addr, length)

    def clear_read_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.remove_breakpoint(3, addr, length)

    def set_access_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.insert_breakpoint(4, addr, length)

    def clear_access_watchpoint(self, addr: int, length: int = 1) -> bool:
        return self.remove_breakpoint(4, addr, length)

    def insert_breakpoint(self, breakpoint_type: int, addr: int, kind: int) -> bool:
        if breakpoint_type not in range(5):
            raise ValueError("breakpoint_type must be in the GDB RSP range 0..4")
        if kind <= 0:
            raise ValueError("kind/length must be positive")
        return self._send_and_expect_ok(f"Z{breakpoint_type},{addr:x},{kind:x}")

    def remove_breakpoint(self, breakpoint_type: int, addr: int, kind: int) -> bool:
        if breakpoint_type not in range(5):
            raise ValueError("breakpoint_type must be in the GDB RSP range 0..4")
        if kind <= 0:
            raise ValueError("kind/length must be positive")
        return self._send_and_expect_ok(f"z{breakpoint_type},{addr:x},{kind:x}")

    def send_command(
        self,
        payload: Union[bytes, str],
        *,
        response_timeout: Optional[float] = -1.0,
    ) -> bytes:
        """Send one RSP command and return one response packet.

        ``response_timeout=None`` waits indefinitely, which is appropriate for
        continue/step packets. The default uses the client's configured timeout.
        """
        self._require_sock()
        payload_b = ascii_payload(payload) if isinstance(payload, str) else payload
        timeout = self.timeout if response_timeout == -1.0 else response_timeout
        with self._command_lock:
            self._send_packet(payload_b)
            return self._recv_packet(timeout=timeout)

    def _send_and_expect_ok(self, payload: Union[bytes, str]) -> bool:
        return self.send_command(payload) == b"OK"

    def _send_packet(self, payload: bytes) -> None:
        self._require_sock()
        pkt = encode_packet(payload)
        while True:
            with self._send_lock:
                self._require_sock()
                self._sock.sendall(pkt)
            if self._no_ack:
                return
            ack = self._recv_ack()
            if ack == b"+":
                return
            if ack == b"-":
                continue
            raise RspProtocolError(f"unexpected ack byte: {ack!r}")

    def _recv_ack(self) -> bytes:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._feed_from_socket()
            ack = self._parser.pop_ack()
            if ack is not None:
                return ack
        raise TimeoutError("timed out waiting for ack")

    def _recv_packet(self, *, timeout: Optional[float]) -> bytes:
        deadline = None if timeout is None else time.monotonic() + timeout
        while deadline is None or time.monotonic() < deadline:
            self._feed_from_socket()
            pkt = self._parser.pop_packet()
            if pkt is None:
                continue
            if not self._no_ack:
                with self._send_lock:
                    self._require_sock()
                    self._sock.sendall(b"+")
            return pkt.payload
        raise TimeoutError("timed out waiting for packet")

    def _feed_from_socket(self) -> None:
        self._require_sock()
        try:
            data = self._sock.recv(4096)
        except socket.timeout:
            return
        if not data:
            raise ConnectionError("RSP connection closed")
        try:
            self._parser.push(data)
        except (RspChecksumError, RspProtocolError):
            if not self._no_ack:
                try:
                    with self._send_lock:
                        self._require_sock()
                        self._sock.sendall(b"-")
                except OSError:
                    pass
            raise

    def _parse_stop_reply(self, payload: bytes) -> StopReply:
        text = payload.decode("ascii", errors="replace")
        if not text:
            return StopReply(raw=text, kind="empty")
        if text[0] in ("S", "T") and len(text) >= 3:
            try:
                sig = int(text[1:3], 16)
            except ValueError:
                sig = None
            return StopReply(raw=text, kind=text[0], signal=sig)
        if text[0] in ("W", "X") and len(text) >= 3:
            return StopReply(raw=text, kind=text[0])
        return StopReply(raw=text, kind="other")

    def _require_sock(self) -> None:
        if self._sock is None:
            raise RuntimeError("not connected; call connect() first")
