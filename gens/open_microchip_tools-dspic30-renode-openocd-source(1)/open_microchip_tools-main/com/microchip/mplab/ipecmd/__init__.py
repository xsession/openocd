from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from mchp_ipecmd.backend import StubBackend
from mchp_ipecmd.client import IpecmdClient
from mchp_ipecmd.server import IpecmdServer


OPFAILURE = 7


@dataclass
class IPECMD:
    """Compatibility shim for `com.microchip.mplab.ipecmd.IPECMD`.

    This Python version focuses on the socket protocol surface.
    """

    backend: StubBackend = StubBackend()

    def runCommandsFromSocket(self, line: str) -> int:
        args = [p for p in str(line).split("#") if p != ""]
        out: List[str] = []
        code = int(self.backend.run(args, out.append))
        if code == 0:
            out.append("Operation Succeeded")
        out.append(f"ERRORCODE:{code}")
        return code

    def run_commands_from_socket(self, line: str) -> int:
        return self.runCommandsFromSocket(line)

    @staticmethod
    def main(args: Optional[Sequence[str]] = None) -> int:
        args = list(args or [])
        if args:
            backend = StubBackend()
            out: List[str] = []
            code = int(backend.run(args, out.append))
            for line in out:
                print(line)
            if code == 0:
                print("Operation Succeeded")
            print(f"ERRORCODE:{code}")
            return code

        port = int(os.getenv("PORTNUMBER", "2012"))
        with IpecmdServer(host="127.0.0.1", port=port, backend=StubBackend()) as srv:
            print(f"IPECMD socket server listening on {srv.host}:{srv.port}")
            try:
                while True:
                    time.sleep(1.0)
            except KeyboardInterrupt:
                return 0


class ServerThread:
    """Compatibility shim for `com.microchip.mplab.ipecmd.ServerThread`.

    This is not a literal thread port; it is provided only so imports succeed.
    """

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs


__all__ = ["IPECMD", "ServerThread", "OPFAILURE", "IpecmdClient", "IpecmdServer"]
