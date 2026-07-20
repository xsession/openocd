from __future__ import annotations

import struct
from dataclasses import dataclass
import math
import time
from typing import Optional, Tuple

from .errors import Ri4ProtocolError
from .errors import Ri4TransportError
from .ri4_com import ComChannel, Ri4Com


def _le_u32(n: int) -> bytes:
    return struct.pack("<I", n & 0xFFFFFFFF)


def _get_le_u32(buf: bytes, offset: int) -> int:
    if offset + 4 > len(buf):
        raise Ri4ProtocolError("Buffer too short for u32")
    return struct.unpack_from("<I", buf, offset)[0]


@dataclass(frozen=True)
class CommandResult:
    status: int
    payload: Optional[bytes]


class ICD4CommsUsb:
    """Python port of key parts of Java ICD4CommsUsb.

    Implements RI4 side-channel header framing and a few small commands.
    """

    PACKET_SIZE = 512
    HEADER_SIZE = 16

    # Side-channel short commands (single byte) / typed commands (u32).
    COMMAND_PROGRESS = 0x84  # -124 signed byte
    COMMAND_ABORT_READ = 0x85  # -123 signed byte
    COMMAND_NUCLEAR_RESET = 0x86  # -122 signed byte
    COMMAND_DETACH = 0x87  # -121 signed byte

    COMMAND_GET_STATUS_FROM_KEY = 261
    COMMAND_ABORT_SCRIPTING_ENGINE = 263
    COMMAND_FLUSH_DATA_DOWNLOAD = 272
    COMMAND_FLUSH_DATA_UPLOAD = 273

    # Script/transfer message types.
    SCRIPT_NO_DATA = 256
    SCRIPT_WITH_DOWNLOAD = -1073741567  # 0xC0000101
    SCRIPT_WITH_UPLOAD = -2147483390  # 0x80000102
    SCRDONE = 259

    # Side-channel response type expected for ACK/RESULT.
    RESULT_RESPONSE_TYPE = 13

    FAST_COMMAND_TIMEOUT_MS = 10_000
    DATA_ENDPOINT_TIMEOUT_MS = 30_000
    GLOBAL_MAX_TIMEOUT_MS = 2_147_483_647

    _RECOVERY_NO_SCRIPT = "no-script"
    _RECOVERY_SCRIPT_NO_DATA = "script-no-data"
    _RECOVERY_SCRIPT_UPLOAD = "script-upload"
    _RECOVERY_SCRIPT_DOWNLOAD = "script-download"

    def __init__(self, com: Ri4Com):
        self.com = com

    def close(self) -> None:
        self.com.close()

    def create_header(
        self,
        job_number: int,
        msg_type: int,
        command_payload: bytes | None,
        transfer_length: int,
        *,
        test_mode: bool = False,
    ) -> bytes:
        seq = 0xFFFFFFFF if test_mode else (job_number & 0xFFFFFFFF)
        payload = command_payload or b""
        bcount = self.HEADER_SIZE + len(payload)
        ocount = transfer_length & 0xFFFFFFFF
        return b"".join(
            [
                _le_u32(msg_type),
                _le_u32(seq),
                _le_u32(bcount),
                _le_u32(ocount),
                payload,
            ]
        )

    def write_side_channel(self, data: bytes, timeout_ms: int) -> None:
        self.com.send(ComChannel.side, data, timeout_ms)

    def read_side_channel(self, length: int, timeout_ms: int) -> bytes:
        return self.com.recv(ComChannel.side, length, timeout_ms)

    def exec_command(self, command_info: bytes, length_of_response: int, timeout_ms: Optional[int] = None) -> bytes:
        if timeout_ms is None or timeout_ms == -1:
            timeout_ms = self.FAST_COMMAND_TIMEOUT_MS
        self.write_side_channel(command_info, timeout_ms)
        response = self.read_side_channel(1024, timeout_ms)
        if len(response) < length_of_response:
            raise Ri4ProtocolError(
                f"Side channel command returned {len(response)} bytes; expected at least {length_of_response}"
            )
        return bytes(response[:length_of_response])

    def get_status(self, job_number: int = 0) -> bytes:
        self.write_side_channel(bytes([self.COMMAND_PROGRESS]), self.GLOBAL_MAX_TIMEOUT_MS)
        return self.read_side_channel(1024, self.GLOBAL_MAX_TIMEOUT_MS)

    def get_status_value_from_key(self, key: str) -> str:
        key_bytes = key.encode("utf-8") + b"\x00"
        header = self.create_header(0, self.COMMAND_GET_STATUS_FROM_KEY, key_bytes, 0)
        self.write_side_channel(header, self.FAST_COMMAND_TIMEOUT_MS)
        buf = self.read_side_channel(1024, self.FAST_COMMAND_TIMEOUT_MS)
        if len(buf) < self.HEADER_SIZE:
            raise Ri4ProtocolError("Side channel response too short")

        # Java parses bytes[16..] as C-string.
        end = buf.find(b"\x00", self.HEADER_SIZE)
        if end == -1:
            raise Ri4ProtocolError("Response not null-terminated")
        return buf[self.HEADER_SIZE : end].decode("utf-8", errors="strict")

    def write_header_and_get_response(self, header: bytes, expected_type: int, timeout_ms: int) -> bytes:
        self.write_side_channel(header, timeout_ms)
        dat = self.read_side_channel(1024, timeout_ms)
        if len(dat) < self.HEADER_SIZE:
            raise Ri4ProtocolError("Side channel response too short")
        got = _get_le_u32(dat, 0)
        if got != (expected_type & 0xFFFFFFFF):
            raise Ri4ProtocolError(f"Unexpected side channel response type: 0x{got:08x}")
        return dat

    def _send_short_command(self, command: int | bytes, timeout_ms: Optional[int] = None) -> bytes:
        if timeout_ms is None:
            timeout_ms = self.FAST_COMMAND_TIMEOUT_MS
        payload = command if isinstance(command, bytes) else self.create_header(0, command, None, 0)
        self.write_side_channel(payload, timeout_ms)
        response = self.read_side_channel(1024, timeout_ms)
        if len(response) < self.HEADER_SIZE:
            raise Ri4ProtocolError("Side channel recovery response too short")
        return response

    def _recover_from_protocol_error(self, recovery_type: str) -> None:
        send_flush_upload = recovery_type == self._RECOVERY_SCRIPT_UPLOAD
        send_flush_download = recovery_type == self._RECOVERY_SCRIPT_DOWNLOAD
        use_nuclear_option = False

        try:
            self._send_short_command(self.COMMAND_ABORT_SCRIPTING_ENGINE)
        except Exception:
            use_nuclear_option = True

        if send_flush_upload and not use_nuclear_option:
            try:
                self._send_short_command(self.COMMAND_FLUSH_DATA_UPLOAD)
            except Exception:
                use_nuclear_option = True

        if send_flush_download and not use_nuclear_option:
            try:
                self._send_short_command(self.COMMAND_FLUSH_DATA_DOWNLOAD)
            except Exception:
                use_nuclear_option = True

        if use_nuclear_option:
            try:
                self._send_short_command(bytes((self.COMMAND_NUCLEAR_RESET,)))
            except Exception:
                return

    def abort_scripting_engine(self, timeout_ms: Optional[int] = None) -> bytes:
        return self._send_short_command(self.COMMAND_ABORT_SCRIPTING_ENGINE, timeout_ms=timeout_ms)

    def send_script_done(self, job_number: int = 0, timeout_ms: Optional[int] = None) -> bytes:
        if timeout_ms is None:
            timeout_ms = self.GLOBAL_MAX_TIMEOUT_MS
        header = self.create_header(job_number, self.SCRDONE, None, 0)
        return self.write_header_and_get_response(header, self.RESULT_RESPONSE_TYPE, timeout_ms)

    def transfer(self, command_payload: Optional[bytes], timeout_ms: Optional[int] = None) -> CommandResult:
        if timeout_ms is None:
            timeout_ms = self.FAST_COMMAND_TIMEOUT_MS
        header = self.create_header(0, self.SCRIPT_NO_DATA, command_payload, 0)
        try:
            response = self.write_header_and_get_response(header, self.RESULT_RESPONSE_TYPE, timeout_ms)
        except (Ri4ProtocolError, Ri4TransportError):
            self._recover_from_protocol_error(self._RECOVERY_SCRIPT_NO_DATA)
            raise
        return self.handle_result(response)

    def read_transfer(
        self, command_payload: Optional[bytes], transfer_data_length: int, timeout_ms: Optional[int] = None
    ) -> Tuple[CommandResult, bytes]:
        if timeout_ms is None:
            timeout_ms = self.FAST_COMMAND_TIMEOUT_MS

        want_len = transfer_data_length
        variable = False
        if want_len == -1:
            want_len = 16384
            variable = True

        header = self.create_header(0, self.SCRIPT_WITH_UPLOAD, command_payload, want_len)
        try:
            ack = self.write_header_and_get_response(header, self.RESULT_RESPONSE_TYPE, timeout_ms)
        except (Ri4ProtocolError, Ri4TransportError):
            self._recover_from_protocol_error(self._RECOVERY_NO_SCRIPT)
            raise
        self.handle_ack(ack)

        data = b""
        if want_len:
            try:
                if variable:
                    data = self.com.recv(ComChannel.data, want_len, self.DATA_ENDPOINT_TIMEOUT_MS)
                else:
                    data = self._recv_exact_data_channel(want_len, self.DATA_ENDPOINT_TIMEOUT_MS)
            except Ri4TransportError:
                self._recover_from_protocol_error(self._RECOVERY_SCRIPT_UPLOAD)
                raise
            if not variable and len(data) != want_len:
                raise Ri4ProtocolError("Data channel length mismatch")

        try:
            result = self.send_script_done(0, timeout_ms=timeout_ms)
        except (Ri4ProtocolError, Ri4TransportError):
            self._recover_from_protocol_error(self._RECOVERY_NO_SCRIPT)
            raise
        cr = self.handle_result(result)
        return cr, data

    def _recv_exact_data_channel(self, want_len: int, timeout_ms: int) -> bytes:
        if want_len <= 0:
            return b""

        deadline = time.monotonic() + (timeout_ms / 1000.0)
        chunks = bytearray()
        while len(chunks) < want_len:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Ri4TransportError(
                    f"Timed out after {timeout_ms} ms while reading {want_len} bytes from RI4 data channel"
                )
            remaining_timeout_ms = min(timeout_ms, max(1, math.ceil(remaining * 1000)))
            piece = self.com.recv(ComChannel.data, want_len - len(chunks), remaining_timeout_ms)
            if not piece:
                raise Ri4TransportError("USB read returned no data on RI4 data channel")
            chunks.extend(piece)
        return bytes(chunks)

    def write_transfer(
        self, command_payload: Optional[bytes], transfer_data: bytes, timeout_ms: Optional[int] = None
    ) -> CommandResult:
        if timeout_ms is None:
            timeout_ms = self.FAST_COMMAND_TIMEOUT_MS

        header = self.create_header(0, self.SCRIPT_WITH_DOWNLOAD, command_payload, len(transfer_data))
        try:
            ack = self.write_header_and_get_response(header, self.RESULT_RESPONSE_TYPE, timeout_ms)
        except (Ri4ProtocolError, Ri4TransportError):
            self._recover_from_protocol_error(self._RECOVERY_NO_SCRIPT)
            raise
        self.handle_ack(ack)

        if transfer_data:
            try:
                self.com.send(ComChannel.data, transfer_data, self.DATA_ENDPOINT_TIMEOUT_MS)
            except Ri4TransportError:
                self._recover_from_protocol_error(self._RECOVERY_SCRIPT_DOWNLOAD)
                raise

        try:
            result = self.send_script_done(0, timeout_ms=timeout_ms)
        except (Ri4ProtocolError, Ri4TransportError):
            self._recover_from_protocol_error(self._RECOVERY_NO_SCRIPT)
            raise
        return self.handle_result(result)

    def handle_ack(self, ack: bytes) -> None:
        if len(ack) < self.HEADER_SIZE:
            raise Ri4ProtocolError("Ack too short")
        bcount = _get_le_u32(ack, 8)
        if bcount > len(ack):
            raise Ri4ProtocolError("Ack bcount exceeds buffer length")
        if bcount == self.HEADER_SIZE:
            return
        if bcount < self.HEADER_SIZE + 4:
            raise Ri4ProtocolError("Ack bcount too small")
        status = _get_le_u32(ack, 16)
        if status != 0:
            raise Ri4ProtocolError(f"Non-zero status in ack: 0x{status:08x}")

    def handle_result(self, response: bytes) -> CommandResult:
        if len(response) < self.HEADER_SIZE:
            raise Ri4ProtocolError("Response too short")
        bcount = _get_le_u32(response, 8)
        if bcount > len(response):
            raise Ri4ProtocolError("Response bcount exceeds buffer length")
        if bcount == self.HEADER_SIZE:
            return CommandResult(0, None)
        if bcount < self.HEADER_SIZE + 8:
            raise Ri4ProtocolError("Response bcount too small")
        status = _get_le_u32(response, 16)
        status_len = _get_le_u32(response, 20)
        payload = None
        if status_len:
            start = 24
            end = start + status_len
            if end > len(response):
                raise Ri4ProtocolError("Response status payload truncated")
            payload = response[start:end]
        return CommandResult(status, payload)
