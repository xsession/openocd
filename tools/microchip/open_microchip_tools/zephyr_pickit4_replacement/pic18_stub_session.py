from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from typing import Dict, Tuple

from mchp_ri4 import Commands, DeviceFile, ICD4CommsUsb, NamedScriptSession, Ri4Com
from mchp_ri4.transport import FakeTransport

from .tools.gen_stub_scripts_xml import build_family_stub_scripts, render_scripts_xml


SUPPORTED_STUB_FAMILIES = (
    "PIC18",
    "PIC16Enhanced",
    "ARM_MPU",
    "PIC32MZ",
    "DSPIC30F",
    "DSPIC33FJ",
    "DSPIC33EP",
    "DSPIC33A",
    "AVR",
)


def _u32le(buf: bytes, off: int = 0) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _ack_ok() -> bytes:
    return b"".join(
        [
            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
            struct.pack("<I", 0),
            struct.pack("<I", 20),
            struct.pack("<I", 0),
            struct.pack("<I", 0),
        ]
    )


def _result_ok() -> bytes:
    return b"".join(
        [
            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
            struct.pack("<I", 0),
            struct.pack("<I", 16),
            struct.pack("<I", 0),
        ]
    )


class StubFamilyProbe:
    STUB_MAGIC0 = 0x5A
    STUB_MAGIC1 = 0xA5
    OP_ENTER_DEBUG_MODE = 0x10
    OP_GET_PC = 0x11
    OP_SET_PC = 0x12
    OP_RUN = 0x13
    OP_HALT = 0x14
    OP_SINGLE_STEP = 0x15
    OP_SINGLE_STEP_UFEX = 0x16
    OP_ERASE_CHIP = 0x20
    OP_WRITE_PROGMEM = 0x21
    OP_READ_PROGMEM = 0x22
    OP_ENTER_TMOD_LV = 0x30
    OP_EXIT_TMOD = 0x31

    def __init__(self, family: str) -> None:
        self.family = family.strip().upper()
        self.pc = 0
        self.debug_mode = False
        self.halted = False
        self.flash = bytearray(b"\xFF" * 4096)
        self.pending_download_address = 0
        self.transport = FakeTransport(on_send=self.on_send)

    def _parse_script_call(self, payload: bytes) -> Tuple[int, bytes]:
        param_size = _u32le(payload, 0)
        script_size = _u32le(payload, 4)
        params = payload[8 : 8 + param_size]
        script = payload[8 + param_size : 8 + param_size + script_size]
        opcode = 0x7F
        if len(script) >= 3 and script[0] == self.STUB_MAGIC0 and script[1] == self.STUB_MAGIC1:
            opcode = script[2]
        return opcode, params

    def get_status_value(self, key: str) -> str:
        normalized = key.strip().lower()
        if normalized == "commands in progress":
            return "0"
        if normalized == "debug mode":
            return "1" if self.debug_mode else "0"
        if normalized == "target halted":
            return "1" if self.halted else "0"
        if normalized == "program counter":
            return f"0x{self.pc:08X}"
        if normalized == "family":
            return self.family
        return "unsupported"

    def on_send(self, ep: int, data: bytes, timeout_ms: int) -> None:
        side_out = 0x02
        side_in = 0x81
        data_out = 0x04
        data_in = 0x83

        if ep == data_out:
            end = self.pending_download_address + len(data)
            self.flash[self.pending_download_address:end] = data
            return

        if ep != side_out or len(data) < 16:
            return

        msg_type = _u32le(data, 0)
        payload = data[16:_u32le(data, 8)]

        if msg_type == ICD4CommsUsb.COMMAND_GET_STATUS_FROM_KEY:
            key = payload.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            value = self.get_status_value(key).encode("utf-8") + b"\x00"
            response = struct.pack("<IIII", ICD4CommsUsb.COMMAND_GET_STATUS_FROM_KEY, 0, 16 + len(value), 0) + value
            self.transport.queue_recv(side_in, response)
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            if opcode in {self.OP_ENTER_DEBUG_MODE, self.OP_ENTER_TMOD_LV}:
                self.debug_mode = True
                self.halted = True
            elif opcode == self.OP_HALT:
                self.debug_mode = True
                self.halted = True
            elif opcode == self.OP_SET_PC and len(params) >= 4:
                self.pc = _u32le(params, 0)
                self.debug_mode = True
                self.halted = True
            elif opcode == self.OP_RUN:
                self.debug_mode = True
                self.halted = False
            elif opcode in {self.OP_SINGLE_STEP, self.OP_SINGLE_STEP_UFEX}:
                self.debug_mode = True
                self.halted = True
                self.pc += 2
            elif opcode == self.OP_ERASE_CHIP:
                self.flash[:] = b"\xFF" * len(self.flash)
            elif opcode == self.OP_EXIT_TMOD:
                self.halted = False
            self.transport.queue_recv(side_in, _result_ok())
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            response = b""
            if opcode == self.OP_GET_PC:
                response = struct.pack("<I", self.pc)
            elif opcode == self.OP_READ_PROGMEM and len(params) >= 8:
                address = _u32le(params, 0)
                size = _u32le(params, 4)
                response = bytes(self.flash[address : address + size])
            self.transport.queue_recv(side_in, _ack_ok())
            self.transport.queue_recv(data_in, response)
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_WITH_DOWNLOAD & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            if opcode == self.OP_WRITE_PROGMEM and len(params) >= 4:
                self.pending_download_address = _u32le(params, 0)
            self.transport.queue_recv(side_in, _ack_ok())
            return

        if msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF):
            self.transport.queue_recv(side_in, _result_ok())


def build_family_stub_xml(family: str = "PIC18", processor: str = "PIC18F_STUB") -> str:
    return render_scripts_xml(processor, build_family_stub_scripts(family))


def create_stub_family_session(family: str = "PIC18", processor: str = "PIC18F_STUB") -> Tuple[NamedScriptSession, StubFamilyProbe]:
    normalized_family = family.strip().upper()
    xml_text = build_family_stub_xml(normalized_family, processor)
    device_file = DeviceFile.from_xml_text(processor, xml_text)
    probe = StubFamilyProbe(normalized_family)
    session = NamedScriptSession(
        commands=Commands(ICD4CommsUsb(Ri4Com(probe.transport))),
        device_file=device_file,
        processor=processor,
        family=normalized_family,
    )
    return session, probe


def generate_stub_family_xml_file(family: str = "PIC18", processor: str = "PIC18F_STUB") -> Path:
    xml_text = build_family_stub_xml(family, processor)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".xml", delete=False)
    try:
        handle.write(xml_text)
    finally:
        handle.close()
    return Path(handle.name)


def build_pic18_stub_xml(processor: str = "PIC18F_STUB") -> str:
    return build_family_stub_xml("PIC18", processor)


def create_pic18_stub_session(processor: str = "PIC18F_STUB") -> Tuple[NamedScriptSession, StubFamilyProbe]:
    return create_stub_family_session("PIC18", processor)


def generate_pic18_stub_xml_file(processor: str = "PIC18F_STUB") -> Path:
    return generate_stub_family_xml_file("PIC18", processor)