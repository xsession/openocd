from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from mchp_mdbcore.simulator import (
    FamilyType,
    MEMTYPE,
    ResetType,
    Simulator,
    SimulatorDataStoreDefault,
    ToolEvent,
)

from .device_catalog import DeviceSpec
from .firmware_image import FirmwareImage


@dataclass(frozen=True)
class TraceEntry:
    pc: int
    bytes_hex: str


class DeviceDataStore(SimulatorDataStoreDefault):
    def __init__(self, spec: DeviceSpec):
        super().__init__()
        # Resize program memory to better match the selected device.
        self._prog = type(self._prog)(spec.program_bytes)
        # dsPIC33 is not PIC32; keep family OTHER.
        self._family = FamilyType.OTHER


class SimpleFirmwareCPU:
    """Very small CPU model: reads N bytes at PC, advances PC, supports breakpoints."""

    def __init__(self, ds: DeviceDataStore, instruction_bytes: int = 2):
        self._ds = ds
        self._pc = 0
        self._covered: List[int] = []
        self._stopwatch = 0
        self._in_halt_notify = False
        self.instruction_bytes = max(1, int(instruction_bytes))
        self.breakpoints: Set[int] = set()
        self.trace_enabled = True
        self._trace: List[TraceEntry] = []

    def init(self, ds: SimulatorDataStoreDefault) -> None:
        return

    def deInit(self) -> None:
        return

    def reset(self, reset_type: ResetType) -> bool:
        self._pc = 0
        self._covered.clear()
        self._trace.clear()
        self._stopwatch = 0
        return True

    def singleStep(self) -> bool:
        pc = int(self._pc)
        self._covered.append(pc)

        data = bytearray(self.instruction_bytes)
        try:
            self._ds.getProgMemory().Read(pc, self.instruction_bytes, data)
        except Exception:
            data = bytearray()

        if self.trace_enabled:
            self._trace.append(TraceEntry(pc=pc, bytes_hex=data.hex().upper()))

        next_pc = pc + self.instruction_bytes
        self._pc = next_pc

        if next_pc in self.breakpoints:
            return False
        return True

    def setPC(self, address: int) -> None:
        self._pc = int(address)

    def getPC(self) -> int:
        return int(self._pc)

    def getStopwatch(self) -> int:
        return int(self._stopwatch)

    def setInHaltNotify(self, v: bool) -> None:
        self._in_halt_notify = bool(v)

    def sendMemoryNotify(self) -> None:
        return

    def getAddressesCovered(self) -> List[int]:
        return list(self._covered)

    def get_trace(self, limit: int = 200) -> List[TraceEntry]:
        if limit <= 0:
            return []
        return list(self._trace[-limit:])


class FirmwareSimulator(Simulator):
    """Simulator variant intended for firmware tracing and debugging UI.

    This is still a high-level tool-facing simulator: it does not attempt to
    faithfully execute dsPIC33 instructions yet, but it supports loading a
    firmware image, stepping, breakpoints, and trace output.
    """

    def __init__(self, device: DeviceSpec):
        super().__init__()
        self._device = device

    def _init(self) -> None:
        self.dataStore = DeviceDataStore(self._device)
        self.dataStore.Init(self.session)
        self.processor = SimpleFirmwareCPU(self.dataStore, instruction_bytes=self._device.instruction_bytes)

        props = self.dataStore.getSimulatorProperties()
        resetTypeSetting = props.get("reset.type")
        if resetTypeSetting is not None and resetTypeSetting == "POR":
            self.resetType = ResetType.POR
        else:
            self.resetType = ResetType.MCLR

        sclResetTypeSetting = props.get("reset.scl")
        if sclResetTypeSetting is not None:
            self.sclReset = sclResetTypeSetting.lower() == "true"

        self.dataStore.getSCL().reset()

    def load_firmware(self, image: FirmwareImage, base_address: int = 0) -> None:
        if self.dataStore is None or self.processor is None:
            self._init()
        assert self.dataStore is not None

        prog = self.dataStore.getProgMemory()

        for seg in image.segments:
            addr = int(seg.address) + int(base_address)
            if addr < 0:
                continue
            # Best-effort write; Memory clamps to its size.
            prog.Write(addr, len(seg.data), seg.data)

        if image.entry_point is not None and self.processor is not None:
            try:
                self.processor.setPC(int(image.entry_point))
            except Exception:
                pass

    def set_breakpoint(self, address: int) -> None:
        if self.processor is None:
            self._init()
        assert isinstance(self.processor, SimpleFirmwareCPU)
        self.processor.breakpoints.add(int(address))

    def clear_breakpoints(self) -> None:
        if self.processor is None:
            self._init()
        assert isinstance(self.processor, SimpleFirmwareCPU)
        self.processor.breakpoints.clear()

    def get_breakpoints(self) -> List[int]:
        if self.processor is None:
            return []
        if not isinstance(self.processor, SimpleFirmwareCPU):
            return []
        return sorted(int(a) for a in self.processor.breakpoints)

    def get_trace(self, limit: int = 200) -> List[TraceEntry]:
        if self.processor is None:
            return []
        if not isinstance(self.processor, SimpleFirmwareCPU):
            return []
        return self.processor.get_trace(limit=limit)

    def RunTarget(self, max_steps: int = 10000) -> bool:  # type: ignore[override]
        assert self.dataStore is not None
        assert self.processor is not None

        num_instructions = 0
        t0 = time.time()

        self.running = True
        self.Notify(ToolEvent.EVENTS.RUN)

        steps_left = int(max_steps)
        while self.running and steps_left > 0:
            cont = self.processor.singleStep()
            self._code_coverage()
            num_instructions += 1
            steps_left -= 1
            if not cont:
                self.running = False

        dt = max(1e-9, time.time() - t0)
        self.instructionsPerSecond = str(int(num_instructions / dt))

        self.processor.setInHaltNotify(True)
        self.processor.sendMemoryNotify()
        self.processor.setInHaltNotify(False)
        self.Notify(ToolEvent.EVENTS.HALT)
        return True
