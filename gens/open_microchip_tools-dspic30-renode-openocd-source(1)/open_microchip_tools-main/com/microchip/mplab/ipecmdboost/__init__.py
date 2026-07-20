from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from mchp_ipecmd.client import IpecmdClient
from mchp_ipecmd.protocol import IpecmdResult


OPFAILURE = 7


@dataclass
class Client:
    """Compatibility shim for `com.microchip.mplab.ipecmdboost.Client`.

    This Python version implements the socket protocol surface only.
    """

    portNumber: int = 2012
    boostCmdString: Optional[Sequence[str]] = None
    hostName: str = "localhost"

    def run(self) -> IpecmdResult:
        args: List[str]
        if self.boostCmdString is None:
            args = []
        elif isinstance(self.boostCmdString, (list, tuple)):
            args = [str(x) for x in self.boostCmdString]
        else:
            args = [str(self.boostCmdString)]

        client = IpecmdClient(host=self.hostName, port=int(self.portNumber))
        return client.send(args)


class InputReader:
    """Compatibility shim for `com.microchip.mplab.ipecmdboost.InputReader`.

    Provided for import compatibility; `Client.run()` returns results directly.
    """

    def __init__(self, *args, **kwargs):
        self.errorCode = OPFAILURE

    def run(self) -> int:
        return int(self.errorCode)


__all__ = ["Client", "InputReader", "OPFAILURE"]
