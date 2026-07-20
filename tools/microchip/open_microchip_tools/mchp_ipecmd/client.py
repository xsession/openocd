from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import List, Sequence

from .protocol import ERROR_PREFIX, IpecmdResult, encode_args


@dataclass
class IpecmdClient:
    host: str = "127.0.0.1"
    port: int = 2012
    timeout_s: float = 5.0

    def send(self, args: Sequence[str]) -> IpecmdResult:
        wire = encode_args(args) + "\n"
        lines: List[str] = []
        error_code = 7

        with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as sock:
            sock.settimeout(self.timeout_s)
            sock.sendall(wire.encode("utf-8"))

            buf = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    text = raw_line.decode("utf-8", errors="replace").rstrip("\r")
                    if text.startswith(ERROR_PREFIX):
                        try:
                            error_code = int(text[len(ERROR_PREFIX) :].strip())
                        except ValueError:
                            error_code = 7
                        return IpecmdResult(lines=lines, error_code=error_code)
                    lines.append(text)

        return IpecmdResult(lines=lines, error_code=error_code)
