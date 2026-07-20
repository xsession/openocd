from __future__ import annotations

import socketserver
import threading
from dataclasses import dataclass, field
from typing import Optional

from .backend import CommandBackend, StubBackend
from .protocol import ERROR_PREFIX, SUCCESS_LINE, decode_line


class _IpecmdHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server: "IpecmdServer" = self.server._owner  # type: ignore[attr-defined]

        raw = self.rfile.readline()
        if not raw:
            return

        line = raw.decode("utf-8", errors="replace")
        args = decode_line(line)

        def emit(msg: str) -> None:
            data = (msg.rstrip("\r\n") + "\n").encode("utf-8")
            self.wfile.write(data)
            self.wfile.flush()

        try:
            code = int(server.backend.run(args, emit))
        except Exception as exc:  # keep protocol stable
            emit(f"Operation Failed ({type(exc).__name__})")
            code = 7

        if code == 0:
            emit(SUCCESS_LINE)

        emit(f"{ERROR_PREFIX}{code}")


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


@dataclass
class IpecmdServer:
    host: str = "127.0.0.1"
    port: int = 0
    backend: CommandBackend = field(default_factory=StubBackend)

    _server: Optional[_ThreadingTCPServer] = None
    _thread: Optional[threading.Thread] = None

    def start(self) -> int:
        if self._server is not None:
            return self.port

        srv = _ThreadingTCPServer((self.host, self.port), _IpecmdHandler)
        srv._owner = self  # type: ignore[attr-defined]
        self._server = srv
        self.port = int(srv.server_address[1])

        t = threading.Thread(target=srv.serve_forever, name="IpecmdServer", daemon=True)
        t.start()
        self._thread = t
        return self.port

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    def __enter__(self) -> "IpecmdServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
