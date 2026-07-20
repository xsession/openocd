from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .errors import Ri4ProtocolError
from .icd4_comms_usb import CommandResult, ICD4CommsUsb
from .script import Script


@dataclass
class Commands:
    """Small Python equivalent of Java Commands.

    This version is intentionally minimal: it executes scripts provided as bytes
    (or a Script object) using the CommUsb-style operations implemented by
    ICD4CommsUsb.
    """

    comm: ICD4CommsUsb
    last_result: Optional[CommandResult] = None

    def close(self) -> None:
        self.comm.close()

    def run_script_basic(self, script_bytes: bytes, *params: Any, timeout_ms: int = -1) -> CommandResult:
        script = Script(method="", data=script_bytes)
        payload = script.add_params(*params)
        cr = self.comm.transfer(payload, timeout_ms=None if timeout_ms == -1 else timeout_ms)
        self.last_result = cr
        if cr.status != 0:
            raise Ri4ProtocolError(f"Script failed: status=0x{cr.status:08x}")
        return cr

    def run_script_with_upload(self, script_bytes: bytes, expected_length: int, *params: Any) -> bytes:
        script = Script(method="", data=script_bytes)
        payload = script.add_params(*params)
        cr, data = self.comm.read_transfer(payload, expected_length)
        self.last_result = cr
        if cr.status != 0:
            raise Ri4ProtocolError(f"Upload script failed: status=0x{cr.status:08x}")
        return data

    def run_script_with_download(self, script_bytes: bytes, data: bytes, *params: Any, timeout_ms: int = -1) -> CommandResult:
        script = Script(method="", data=script_bytes)
        payload = script.add_params(*params)
        cr = self.comm.write_transfer(payload, data, timeout_ms=None if timeout_ms == -1 else timeout_ms)
        self.last_result = cr
        if cr.status != 0:
            raise Ri4ProtocolError(f"Download script failed: status=0x{cr.status:08x}")
        return cr
