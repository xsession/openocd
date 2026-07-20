from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Union

from .errors import Ri4ProtocolError


@dataclass(frozen=True)
class Script:
    """RI4 script wrapper.

    Matches the Java behavior:
    addParams() prepends:
      - u32le paramSizeBytes
      - u32le scriptDataLength
      - concatenated param blobs
      - raw script bytes
    """

    method: str
    data: bytes

    # Java-compat accessors
    def getMethod(self) -> str:
        return self.method

    def getData(self) -> bytes:
        return self.data

    def add_params(self, *params: Any) -> bytes:
        blobs = collect_params(params)
        param_size = sum(len(b) for b in blobs)
        header = struct.pack("<II", param_size, len(self.data))
        return header + b"".join(blobs) + self.data

    def addParams(self, *params: Any) -> bytes:
        return self.add_params(*params)


def _u32le(n: int) -> bytes:
    return struct.pack("<I", n & 0xFFFFFFFF)


def collect_params(params: Sequence[Any]) -> List[bytes]:
    out: List[bytes] = []
    for p in params:
        if isinstance(p, bool):
            # Avoid bool being treated as int.
            out.append(struct.pack("<B", 1 if p else 0))
        elif isinstance(p, int):
            out.append(_u32le(p))
        elif isinstance(p, (bytes, bytearray)):
            b = bytes(p)
            out.append(b + b"\x00")
        elif isinstance(p, str):
            out.append(p.encode("utf-16le"))
        else:
            raise Ri4ProtocolError(f"Unknown parameter type: {type(p).__name__}")
    return out
