from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import Ri4TransportError
from .transport import ToolTransport


class ComChannel(Enum):
    side = "side"
    data = "data"
    streaming = "streaming"


@dataclass(frozen=True)
class EndpointMap:
    side_out: int
    side_in: int
    data_out: int
    data_in: int
    streaming_ep: int


# Defaults match the RI4Com static defaults used by PK4/ICD5 in mdbcore.
DEFAULT_ENDPOINTS = EndpointMap(
    side_out=0x02,
    side_in=0x81,
    data_out=0x04,
    data_in=0x83,
    streaming_ep=0x03,
)


class Ri4Com:
    """Minimal RI4ComInterface-like wrapper over a ToolTransport."""

    def __init__(self, transport: ToolTransport, endpoints: EndpointMap = DEFAULT_ENDPOINTS):
        self._transport = transport
        self._ep = endpoints

    def _ep_for(self, channel: ComChannel, *, direction: str) -> int:
        if channel == ComChannel.side:
            return self._ep.side_out if direction == "out" else self._ep.side_in
        if channel == ComChannel.data:
            return self._ep.data_out if direction == "out" else self._ep.data_in
        if channel == ComChannel.streaming:
            # Streaming is typically IN-only.
            return self._ep.streaming_ep
        raise Ri4TransportError(f"Unknown channel: {channel}")

    def send(self, channel: ComChannel, data: bytes, timeout_ms: int) -> None:
        ep = self._ep_for(channel, direction="out")
        self._transport.send(ep, data, timeout_ms)

    def recv(self, channel: ComChannel, length: int, timeout_ms: int) -> bytes:
        ep = self._ep_for(channel, direction="in")
        return self._transport.recv(ep, length, timeout_ms)

    def close(self) -> None:
        self._transport.close()
