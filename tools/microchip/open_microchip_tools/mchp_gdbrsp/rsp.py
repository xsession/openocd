from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


_ACK = b"+"
_NAK = b"-"
_START = ord("$")
_END = ord("#")
_ESCAPE = ord("}")
_XOR = 0x20


class RspChecksumError(ValueError):
    pass


class RspProtocolError(ValueError):
    pass


def checksum(payload: bytes) -> int:
    return sum(payload) & 0xFF


def checksum_hex(payload: bytes) -> bytes:
    return f"{checksum(payload):02x}".encode("ascii")


def _needs_escape(b: int) -> bool:
    return b in (_START, _END, _ESCAPE)


def escape_payload(payload: bytes) -> bytes:
    out = bytearray()
    for b in payload:
        if _needs_escape(b):
            out.append(_ESCAPE)
            out.append(b ^ _XOR)
        else:
            out.append(b)
    return bytes(out)


def unescape_payload(payload: bytes) -> bytes:
    out = bytearray()
    it = iter(payload)
    for b in it:
        if b == _ESCAPE:
            try:
                nxt = next(it)
            except StopIteration as e:
                raise RspProtocolError("dangling escape") from e
            out.append(nxt ^ _XOR)
        else:
            out.append(b)
    return bytes(out)


def encode_packet(payload: bytes) -> bytes:
    esc = escape_payload(payload)
    return b"$" + esc + b"#" + checksum_hex(payload)


@dataclass(frozen=True)
class DecodedPacket:
    payload: bytes


class RspStreamParser:
    """Incremental parser for an RSP byte stream.

    Feed bytes via `push()`; retrieve decoded packets via `pop_packet()`.
    ACK/NAK are handled as single-byte events via `pop_ack()`.
    """

    def __init__(self):
        self._buf = bytearray()
        self._acks: bytearray = bytearray()
        self._packets: List[DecodedPacket] = []

    def push(self, data: bytes) -> None:
        self._buf.extend(data)
        self._drain()

    def pop_ack(self) -> Optional[bytes]:
        if not self._acks:
            return None
        b = bytes([self._acks.pop(0)])
        return b

    def pop_packet(self) -> Optional[DecodedPacket]:
        if not self._packets:
            return None
        return self._packets.pop(0)

    def _drain(self) -> None:
        while self._buf:
            # ACK/NAK are out-of-band *between* packets. Do not treat '+'/'-' as
            # ACK/NAK when inside a packet payload.
            if self._buf[0] in (_ACK[0], _NAK[0]):
                self._acks.append(self._buf.pop(0))
                continue

            try:
                start_idx = self._buf.index(_START)
            except ValueError:
                if len(self._buf) > 4096:
                    self._buf.clear()
                return

            if start_idx:
                # Drop noise before '$'
                del self._buf[:start_idx]
                continue

            # Buffer starts with '$' now.
            try:
                hash_idx = self._buf.index(_END)
            except ValueError:
                return

            if len(self._buf) < hash_idx + 3:
                return

            esc_payload = bytes(self._buf[1:hash_idx])
            cs = bytes(self._buf[hash_idx + 1 : hash_idx + 3])
            del self._buf[: hash_idx + 3]

            try:
                expected = int(cs.decode("ascii"), 16)
            except ValueError as e:
                raise RspProtocolError(f"invalid checksum bytes: {cs!r}") from e

            payload = unescape_payload(esc_payload)
            actual = checksum(payload)
            if actual != expected:
                raise RspChecksumError(f"checksum mismatch: expected {expected:02x}, got {actual:02x}")

            self._packets.append(DecodedPacket(payload=payload))


def bytes_to_hex(data: bytes) -> str:
    return data.hex()


def hex_to_bytes(text: str) -> bytes:
    if len(text) % 2 != 0:
        raise ValueError("hex string must have even length")
    return bytes.fromhex(text)


def ascii_payload(s: str) -> bytes:
    return s.encode("ascii")


def iter_kv_semi(s: str) -> Iterable[str]:
    for part in s.split(";"):
        part = part.strip()
        if part:
            yield part
