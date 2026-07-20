from __future__ import annotations

import struct
import textwrap
from typing import Tuple

from mchp_ri4 import Commands, DeviceFile, ICD4CommsUsb, NamedScriptSession, Ri4Com
from mchp_ri4.transport import FakeTransport

from .pk4_observed_profile import PK4_APP2_BASE, PK4_APP_BASE, Pk4ObservedProbeModel


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


class Pk4ObservedRi4Probe:
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
    OP_WRITE_PRIMARY_SLOT = 0x23
    OP_READ_PRIMARY_SLOT = 0x24
    OP_WRITE_SECONDARY_SLOT = 0x25
    OP_READ_SECONDARY_SLOT = 0x26
    OP_ENTER_TMOD_LV = 0x30
    OP_EXIT_TMOD = 0x31

    def __init__(self) -> None:
        self.model = Pk4ObservedProbeModel(debug_mode=True, halted=True)
        self.pending_download_address = 0
        self.transport = FakeTransport(on_send=self.on_send)

    def get_status_value(self, key: str) -> str:
        return self.model.get_status_value(key)

    def _parse_script_call(self, payload: bytes) -> Tuple[int, bytes]:
        param_size = _u32le(payload, 0)
        script_size = _u32le(payload, 4)
        params = payload[8 : 8 + param_size]
        script = payload[8 + param_size : 8 + param_size + script_size]
        opcode = 0x7F
        if len(script) >= 3 and script[0] == self.STUB_MAGIC0 and script[1] == self.STUB_MAGIC1:
            opcode = script[2]
        return opcode, params

    def on_send(self, ep: int, data: bytes, timeout_ms: int) -> None:
        del timeout_ms

        side_out = 0x02
        side_in = 0x81
        data_out = 0x04
        data_in = 0x83

        if ep == data_out:
            self.model.write_program(self.pending_download_address, data)
            self.pending_download_address += len(data)
            return

        if ep != side_out or len(data) < 16:
            return

        msg_type = _u32le(data, 0)
        payload = data[16 : _u32le(data, 8)]

        if msg_type == ICD4CommsUsb.COMMAND_GET_STATUS_FROM_KEY:
            key = payload.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            value = self.model.get_status_value(key).encode("utf-8") + b"\x00"
            response = struct.pack("<IIII", ICD4CommsUsb.COMMAND_GET_STATUS_FROM_KEY, 0, 16 + len(value), 0) + value
            self.transport.queue_recv(side_in, response)
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            if opcode in {self.OP_ENTER_DEBUG_MODE, self.OP_ENTER_TMOD_LV}:
                self.model.debug_mode = True
                self.model.halted = True
            elif opcode == self.OP_HALT:
                self.model.debug_mode = True
                self.model.halted = True
            elif opcode == self.OP_SET_PC and len(params) >= 4:
                self.model.pc = _u32le(params, 0)
                self.model.debug_mode = True
                self.model.halted = True
            elif opcode == self.OP_RUN:
                self.model.debug_mode = True
                self.model.halted = False
            elif opcode in {self.OP_SINGLE_STEP, self.OP_SINGLE_STEP_UFEX}:
                self.model.debug_mode = True
                self.model.halted = True
                self.model.pc += 2
            elif opcode == self.OP_ERASE_CHIP:
                self.model.erase_chip()
            elif opcode == self.OP_EXIT_TMOD:
                self.model.halted = False
            self.transport.queue_recv(side_in, _result_ok())
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            response = b""
            if opcode == self.OP_GET_PC:
                response = struct.pack("<I", self.model.pc)
            elif opcode == self.OP_READ_PROGMEM and len(params) >= 8:
                address = _u32le(params, 0)
                size = _u32le(params, 4)
                response = self.model.read_program(address, size)["data"]
            elif opcode == self.OP_READ_PRIMARY_SLOT and len(params) >= 8:
                offset = _u32le(params, 0)
                size = _u32le(params, 4)
                response = self.model.read_program(PK4_APP_BASE + offset, size)["data"]
            elif opcode == self.OP_READ_SECONDARY_SLOT and len(params) >= 8:
                offset = _u32le(params, 0)
                size = _u32le(params, 4)
                response = self.model.read_program(PK4_APP2_BASE + offset, size)["data"]
            self.transport.queue_recv(side_in, _ack_ok())
            self.transport.queue_recv(data_in, response)
            return

        if msg_type == (ICD4CommsUsb.SCRIPT_WITH_DOWNLOAD & 0xFFFFFFFF):
            opcode, params = self._parse_script_call(payload)
            if opcode == self.OP_WRITE_PROGMEM and len(params) >= 4:
                self.pending_download_address = _u32le(params, 0)
            elif opcode == self.OP_WRITE_PRIMARY_SLOT and len(params) >= 4:
                self.pending_download_address = PK4_APP_BASE + _u32le(params, 0)
            elif opcode == self.OP_WRITE_SECONDARY_SLOT and len(params) >= 4:
                self.pending_download_address = PK4_APP2_BASE + _u32le(params, 0)
            self.transport.queue_recv(side_in, _ack_ok())
            return

        if msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF):
            self.transport.queue_recv(side_in, _result_ok())


class Pk4ObservedNamedSession(NamedScriptSession):
    def get_status_value(self, key: str) -> str:
        return self.commands.comm.get_status_value_from_key(key)

    def write_primary_slot(self, offset: int, data: bytes) -> dict:
        return self.run_script_with_download("WritePrimarySlot", data, offset, len(data))

    def read_primary_slot(self, offset: int, length: int) -> dict:
        data = self.run_script_with_upload("ReadPrimarySlot", length, offset, length)
        return {"address": PK4_APP_BASE + offset, "length": len(data), "dataHex": data.hex(), "script": "ReadPrimarySlot"}

    def write_secondary_slot(self, offset: int, data: bytes) -> dict:
        return self.run_script_with_download("WriteSecondarySlot", data, offset, len(data))

    def read_secondary_slot(self, offset: int, length: int) -> dict:
        data = self.run_script_with_upload("ReadSecondarySlot", length, offset, length)
        return {"address": PK4_APP2_BASE + offset, "length": len(data), "dataHex": data.hex(), "script": "ReadSecondarySlot"}


def build_pk4_observed_xml(processor: str = "ATSAME70_PK4_OBS") -> str:
    return textwrap.dedent(
        f"""
        <devicefile>
          <processor>{processor}</processor>
          <script><function>EnterDebugMode</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x10</byte></scrbytes></script>
          <script><function>GetPC</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x11</byte></scrbytes></script>
          <script><function>SetPC</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x12</byte></scrbytes></script>
          <script><function>Run</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x13</byte></scrbytes></script>
          <script><function>Halt</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x14</byte></scrbytes></script>
          <script><function>SingleStep</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x15</byte></scrbytes></script>
          <script><function>SingleStepUFEX</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x16</byte></scrbytes></script>
          <script><function>EraseChip</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x20</byte></scrbytes></script>
          <script><function>WriteProgmem</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x21</byte></scrbytes></script>
          <script><function>ReadProgmem</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x22</byte></scrbytes></script>
                    <script><function>WritePrimarySlot</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x23</byte></scrbytes></script>
                    <script><function>ReadPrimarySlot</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x24</byte></scrbytes></script>
                    <script><function>WriteSecondarySlot</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x25</byte></scrbytes></script>
                    <script><function>ReadSecondarySlot</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x26</byte></scrbytes></script>
          <script><function>EnterTmodLV</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x30</byte></scrbytes></script>
          <script><function>ExitTmod</function><scrbytes><byte>0x5A</byte><byte>0xA5</byte><byte>0x31</byte></scrbytes></script>
        </devicefile>
        """
    ).strip()


def create_pk4_observed_session(processor: str = "ATSAME70_PK4_OBS") -> Tuple[Pk4ObservedNamedSession, Pk4ObservedRi4Probe]:
    device_file = DeviceFile.from_xml_text(processor, build_pk4_observed_xml(processor))
    probe = Pk4ObservedRi4Probe()
    session = Pk4ObservedNamedSession(
        commands=Commands(ICD4CommsUsb(Ri4Com(probe.transport))),
        device_file=device_file,
        processor=processor,
        family="ARM_MPU",
    )
    return session, probe