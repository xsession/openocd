from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict

from .commands import Commands
from .errors import Ri4ProtocolError
from .errors import Ri4TransportError


def _u32le(buf: bytes, offset: int) -> int:
    if offset + 4 > len(buf):
        raise Ri4ProtocolError("Power status payload is truncated")
    return struct.unpack_from("<I", buf, offset)[0]


def _u16_bytes(value: int) -> bytes:
    if value < 0 or value > 0xFFFF:
        raise Ri4ProtocolError(f"Power value out of range: {value}")
    return bytes((value & 0xFF, (value >> 8) & 0xFF, 0x00, 0x00))


def build_live_connect_script(enable: bool) -> bytes:
    return bytes((0x39, 0x01 if enable else 0x00))


def build_select_power_source_script(from_tool: bool) -> bytes:
    return bytes((0x46, 0x01 if from_tool else 0x00, 0x00, 0x00, 0x00))


def build_shutdown_power_script() -> bytes:
    return bytes((0x44,))


def build_maintain_active_power_script(enable: bool) -> bytes:
    return bytes((0x00, 0x01 if enable else 0x00))


def build_power_status_script() -> bytes:
    return bytes((0x47,))


def build_init_power_script(vdd_mv: int, vpp_operation_mv: int, vpp_on_mv: int) -> bytes:
    return b"".join(
        [
            bytes((0x40,)),
            _u16_bytes(vdd_mv),
            _u16_bytes(vpp_operation_mv),
            _u16_bytes(vpp_on_mv),
            bytes((0x42, 0x43)),
        ]
    )


@dataclass(frozen=True)
class PowerStatus:
    internal_vdd_mv: int
    target_vdd_mv: int
    target_vpp_mv: int
    internal_vpp_mv: int
    vdd_sense_mv: int
    temperature_raw: int
    vdd_current_sense_raw: int
    vdd_voltage_sense_mv: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "internalVddMv": self.internal_vdd_mv,
            "targetVddMv": self.target_vdd_mv,
            "targetVppMv": self.target_vpp_mv,
            "internalVppMv": self.internal_vpp_mv,
            "vddSenseMv": self.vdd_sense_mv,
            "temperatureRaw": self.temperature_raw,
            "vddCurrentSenseRaw": self.vdd_current_sense_raw,
            "vddVoltageSenseMv": self.vdd_voltage_sense_mv,
        }


def parse_power_status_payload(payload: bytes) -> PowerStatus:
    if len(payload) < 32:
        raise Ri4ProtocolError("Power status payload must contain at least 32 bytes")
    return PowerStatus(
        internal_vdd_mv=_u32le(payload, 0),
        target_vdd_mv=_u32le(payload, 4),
        target_vpp_mv=_u32le(payload, 8),
        internal_vpp_mv=_u32le(payload, 12),
        vdd_sense_mv=_u32le(payload, 16),
        temperature_raw=_u32le(payload, 20),
        vdd_current_sense_raw=_u32le(payload, 24),
        vdd_voltage_sense_mv=_u32le(payload, 28),
    )


class Ri4PowerController:
    POWER_SCRIPT_TIMEOUT_MS = 30_000

    def __init__(self, commands: Commands):
        self._commands = commands

    def _preclean_scripting_engine(self) -> None:
        try:
            self._commands.comm.abort_scripting_engine(timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS)
        except Exception:
            return

    def set_live_connect(self, enable: bool) -> Dict[str, object]:
        result = self._commands.run_script_basic(
            build_live_connect_script(enable),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        return {"liveConnect": enable, "status": result.status}

    def select_power_source(self, from_tool: bool) -> Dict[str, object]:
        result = self._commands.run_script_basic(
            build_select_power_source_script(from_tool),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        return {"fromTool": from_tool, "status": result.status}

    def shutdown_power(self) -> Dict[str, object]:
        result = self._commands.run_script_basic(
            build_shutdown_power_script(),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        return {"powered": False, "status": result.status}

    def set_maintain_active_power(self, enable: bool) -> Dict[str, object]:
        result = self._commands.run_script_basic(
            build_maintain_active_power_script(enable),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        return {"maintainActive": enable, "status": result.status}

    def init_power(self, voltage_mv: int, *, use_low_voltage_programming: bool = True, vpp_program_mv: int = 12000) -> Dict[str, object]:
        vpp_operation_mv = voltage_mv if use_low_voltage_programming else vpp_program_mv
        result = self._commands.run_script_basic(
            build_init_power_script(voltage_mv, vpp_operation_mv, voltage_mv),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        return {
            "voltageMv": voltage_mv,
            "vppOperationMv": vpp_operation_mv,
            "vppOnMv": voltage_mv,
            "lowVoltageProgramming": use_low_voltage_programming,
            "status": result.status,
        }

    def get_power_status(self) -> Dict[str, int]:
        result = self._commands.run_script_basic(
            build_power_status_script(),
            timeout_ms=self.POWER_SCRIPT_TIMEOUT_MS,
        )
        payload = result.payload or b""
        return parse_power_status_payload(payload).to_dict()

    def power_target(
        self,
        voltage_mv: int,
        *,
        from_tool: bool = True,
        maintain_active: bool = True,
        live_connect: bool = True,
        use_low_voltage_programming: bool = True,
        vpp_program_mv: int = 12000,
    ) -> Dict[str, object]:
        last_error = None
        for _ in range(2):
            self._preclean_scripting_engine()
            try:
                if live_connect:
                    self.set_live_connect(True)
                self.select_power_source(from_tool)
                self.shutdown_power()
                if not from_tool:
                    if maintain_active:
                        raise Ri4ProtocolError("maintain_active requires tool-supplied power")
                    return {
                        "fromTool": False,
                        "liveConnect": live_connect,
                        "maintainActive": False,
                        "status": self.get_power_status(),
                    }
                self.init_power(
                    voltage_mv,
                    use_low_voltage_programming=use_low_voltage_programming,
                    vpp_program_mv=vpp_program_mv,
                )
                self.set_maintain_active_power(maintain_active)
                return {
                    "fromTool": True,
                    "liveConnect": live_connect,
                    "maintainActive": maintain_active,
                    "requestedVoltageMv": voltage_mv,
                    "lowVoltageProgramming": use_low_voltage_programming,
                    "status": self.get_power_status(),
                }
            except (Ri4ProtocolError, Ri4TransportError) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise Ri4ProtocolError("power_target failed without a captured error")