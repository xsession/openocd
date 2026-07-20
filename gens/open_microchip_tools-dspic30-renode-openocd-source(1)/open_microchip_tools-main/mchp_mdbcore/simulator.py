from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Collection, Dict, List, Optional, Protocol


class MEMTYPE(Enum):
    FILE_REGISTERS = "FILE_REGISTERS"
    NMMR = "NMMR"
    PROGRAM_MEMORY = "PROGRAM_MEMORY"
    PERIPHERAL_MEMORY = "PERIPHERAL_MEMORY"


class ResetType(Enum):
    MCLR = "MCLR"
    POR = "POR"


class ToolEvent:
    class EVENTS(Enum):
        PROGRAM_START = "PROGRAM_START"
        PROGRAM_DONE = "PROGRAM_DONE"
        RUN = "RUN"
        HALT = "HALT"


class Observer(Protocol):
    def Update(self, obj: Any) -> None:
        ...


class Memory:
    def __init__(self, size: int = 0x10000):
        self._buf = bytearray(size)

    def Read(self, address: int, size: int, data: bytearray) -> int:
        a = int(address)
        n = int(size)
        if n <= 0:
            return 0
        end = min(a + n, len(self._buf))
        read_n = max(0, end - a)
        data[:read_n] = self._buf[a:end]
        return read_n

    def Write(self, address: int, size: int, data: bytes) -> int:
        a = int(address)
        n = int(size)
        if n <= 0:
            return 0
        end = min(a + n, len(self._buf))
        write_n = max(0, end - a)
        self._buf[a:end] = data[:write_n]
        return write_n


class SimulatorProperties:
    """Pythonic tool-properties bag with Java-name shims.

    Java surface mirrored:
      - `get(key)` and `get(key, default)`
      - `set(key, value)`
      - `deInit()`
    """

    def __init__(self, initial: Optional[Dict[str, str]] = None):
        self._d: Dict[str, str] = dict(initial or {})

    # Pythonic API
    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._d.get(key, default)

    def set_value(self, key: str, value: str) -> None:
        self._d[str(key)] = str(value)

    def de_init(self) -> None:
        self._d.clear()

    # Java-name shims
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.get_value(key, default)

    def set(self, key: str, value: str) -> None:
        self.set_value(key, value)

    def deInit(self) -> None:
        self.de_init()


class SimulatorPropertiesDefault(SimulatorProperties):
    """Mirrors Java `SimulatorPropertiesDefault` behavior.

    If `assembly` provides `GetToolProperties()`, values are synced from/to it.
    """

    def __init__(self, assembly: Any, initial: Optional[Dict[str, str]] = None):
        super().__init__(initial)
        self._assembly: Any = assembly

    def update_values(self) -> None:
        properties = None
        if self._assembly is not None and hasattr(self._assembly, "GetToolProperties"):
            properties = self._assembly.GetToolProperties()

        if properties is None:
            return

        items: Iterable[Any]
        if hasattr(properties, "items"):
            items = properties.items()
        else:
            # Fallback: treat as iterable of keys.
            items = ((k, properties[k]) for k in properties)

        self._d.clear()
        for k, v in items:
            self._d[str(k)] = None if v is None else str(v)

    def set_value(self, key: str, value: str) -> None:
        properties = None
        if self._assembly is not None and hasattr(self._assembly, "GetToolProperties"):
            properties = self._assembly.GetToolProperties()

        if properties is None:
            return

        super().set_value(key, value)
        if hasattr(properties, "setProperty"):
            properties.setProperty(str(key), str(value))
        else:
            try:
                properties[str(key)] = str(value)
            except Exception:
                return

    def de_init(self) -> None:
        self._assembly = None
        super().de_init()

    # Java-name shims
    def updateValues(self) -> None:
        self.update_values()


class SimulatorStreamingDataMediator:
    def start(self) -> int:
        return 0

    def stop(self) -> int:
        return 0


class SCL:
    def run(self) -> None:
        return

    def reset(self) -> None:
        return

    def deviceReset(self) -> None:
        return


class PIC32Memories:
    def __init__(self, file_mem: Memory, prog_mem: Memory, peripheral_mem: Memory):
        self._file = file_mem
        self._prog = prog_mem
        self._periph = peripheral_mem

    def getFileMemory(self) -> Memory:
        return self._file

    def getProgMemory(self) -> Memory:
        return self._prog

    def getPeripheralMemory(self) -> Memory:
        return self._periph


class FamilyType(Enum):
    OTHER = "OTHER"
    PIC32 = "PIC32"


class SimulatorDataStoreDefault:
    def __init__(self):
        self._family = FamilyType.OTHER
        self._debug_ips = False
        self._in_debug_reset = False

        self._sfr = Memory()
        self._nmmr = Memory()
        self._prog = Memory()
        self._file = Memory()
        self._periph = Memory()
        self._pic32 = PIC32Memories(self._file, self._prog, self._periph)

        self._props = SimulatorProperties({"reset.type": "MCLR", "reset.scl": "false"})
        self._scl = SCL()
        self._sdm = SimulatorStreamingDataMediator()

    def Init(self, session: Any) -> None:
        return

    def getDebugIPS(self) -> bool:
        return self._debug_ips

    def getDeviceFamily(self) -> FamilyType:
        return self._family

    def setDeviceFamily(self, fam: FamilyType) -> None:
        self._family = fam

    def setInDebugReset(self, v: bool) -> None:
        self._in_debug_reset = bool(v)

    def getSFRMemory(self) -> Memory:
        return self._sfr

    def getNMMRMemory(self) -> Memory:
        return self._nmmr

    def getProgMemory(self) -> Memory:
        return self._prog

    def getFileMemory(self) -> Memory:
        return self._file

    def getPic32PhysicalMems(self) -> PIC32Memories:
        return self._pic32

    def getSimulatorProperties(self) -> SimulatorProperties:
        return self._props

    def getSCL(self) -> SCL:
        return self._scl

    def getSimulatorStreamingDataMediator(self) -> SimulatorStreamingDataMediator:
        return self._sdm

    def getNominalVoltage(self) -> float:
        return 3.3


class Processor:
    def __init__(self):
        self._pc = 0
        self._stopwatch = 0
        self._in_halt_notify = False
        self._covered: List[int] = []
        self.halt_after_steps: int = 1
        self._step_count = 0

    def init(self, ds: SimulatorDataStoreDefault) -> None:
        return

    def deInit(self) -> None:
        return

    def reset(self, reset_type: ResetType) -> bool:
        self._pc = 0
        self._step_count = 0
        self._covered.clear()
        self._stopwatch = 0
        return True

    def singleStep(self) -> bool:
        self._pc += 1
        self._covered.append(self._pc)
        self._step_count += 1
        return self._step_count < self.halt_after_steps

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


@dataclass
class _ObserverWrapper:
    fn: Callable[[Any], None]

    def Update(self, obj: Any) -> None:
        self.fn(obj)


class Simulator:
    """Minimal, runnable clean-room port of Java `Simulator`.

    This is not a full CPU simulator; it preserves the tool-facing surface so other
    layers can integrate and tests can exercise the sequencing.
    """

    def __init__(self):
        self.dataStore: Optional[SimulatorDataStoreDefault] = None
        self.processor: Optional[Processor] = None
        self.running = False
        self.observers: List[Observer] = []
        self.session: Any = None

        self.codeCoverageData: Dict[int, int] = {}
        self.codeCoverageEnabled = False
        self.resetType = ResetType.MCLR
        self.sclReset = False
        self.instructionsPerSecond: Optional[str] = None

    # Java naming
    def Abort(self) -> None:
        self.running = False

    def SetHWTool(self, Tool: Any) -> None:
        return

    def getLivePeripheralLocalizedNames(self) -> List[str]:
        return []

    def Engage(self, S: Any) -> None:
        self.session = S
        self._init()

    def Dismiss(self) -> None:
        self.running = False
        if self.processor is not None:
            self.processor.deInit()
        self.processor = None
        self.dataStore = None
        self.session = None

    def _init(self) -> None:
        self.dataStore = SimulatorDataStoreDefault()
        self.dataStore.Init(self.session)
        self.processor = Processor()
        self.processor.init(self.dataStore)

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

    def ConnectToTool(self, type: Any = None) -> bool:
        return self._start_debug_session()

    def ProgramTarget(self, op: Any = None) -> bool:
        self.Notify(ToolEvent.EVENTS.PROGRAM_START)
        ok = self._start_debug_session()
        self.Notify(ToolEvent.EVENTS.PROGRAM_DONE)
        return ok

    def _start_debug_session(self) -> bool:
        if self.dataStore is None or self.processor is None:
            # allow direct use without Engage()
            self._init()
        assert self.dataStore is not None
        assert self.processor is not None

        self.processor.reset(ResetType.POR)
        self._reset_vdd_vss_to_nominal_voltage()
        return True

    def HoldTargetInReset(self) -> None:
        return

    def ReleaseTargetFromReset(self) -> None:
        return

    def ReadTarget(self) -> bool:
        return True

    def RunTarget(self) -> bool:
        assert self.dataStore is not None
        assert self.processor is not None

        debug = self.dataStore.getDebugIPS()
        num_instructions = 0
        t0 = time.time()

        self.running = True
        self.Notify(ToolEvent.EVENTS.RUN)
        while self.running:
            cont = self.processor.singleStep()
            self._code_coverage()
            num_instructions += 1
            if not cont:
                self.running = False

        if debug:
            dt = max(1e-9, time.time() - t0)
            ips = int(num_instructions / dt)
            self.instructionsPerSecond = str(ips)

        self.processor.setInHaltNotify(True)
        self.processor.sendMemoryNotify()
        self.processor.setInHaltNotify(False)
        self.Notify(ToolEvent.EVENTS.HALT)
        return True

    def getInstructionsPerSecond(self) -> Optional[str]:
        return self.instructionsPerSecond

    def SingleStepTarget(self) -> bool:
        assert self.processor is not None
        ok = self.processor.singleStep()
        self._code_coverage()
        self.processor.setInHaltNotify(True)
        self.processor.sendMemoryNotify()
        self.processor.setInHaltNotify(False)
        return ok

    def BeginFastOp(self) -> bool:
        return True

    def FastStep(self) -> bool:
        return self.SingleStepTarget()

    def EndFastOp(self) -> bool:
        if self.processor is not None:
            self.processor.setInHaltNotify(True)
            self.processor.sendMemoryNotify()
            self.processor.setInHaltNotify(False)
        return True

    def VerifyTarget(self) -> bool:
        return True

    def EraseTarget(self) -> bool:
        return True

    def BlankCheckTarget(self) -> bool:
        return True

    def HaltTarget(self) -> bool:
        self.running = False
        return True

    def ResetTarget(self) -> bool:
        if self.dataStore is not None:
            self.dataStore.setInDebugReset(True)
        try:
            if self.dataStore is not None:
                props = self.dataStore.getSimulatorProperties()
                resetTypeSetting = props.get("reset.type")
                if resetTypeSetting is not None and resetTypeSetting == "POR":
                    self.resetType = ResetType.POR
                else:
                    self.resetType = ResetType.MCLR

            if self.processor is None:
                self._init()
            assert self.processor is not None
            ok = self.processor.reset(self.resetType)

            if self.sclReset and self.dataStore is not None:
                self.dataStore.getSCL().deviceReset()
            return ok
        finally:
            if self.dataStore is not None:
                self.dataStore.setInDebugReset(False)

    def SetPC(self, address: int) -> None:
        assert self.processor is not None
        self.processor.setPC(address)

    def GetPC(self) -> int:
        assert self.processor is not None
        return self.processor.getPC()

    def GetPreviousPC(self) -> int:
        return (1 << 63) - 1

    def TestTool(self) -> None:
        return

    def getDataStore(self) -> Optional[SimulatorDataStoreDefault]:
        return self.dataStore

    def getSCL(self) -> Optional[SCL]:
        return None if self.dataStore is None else self.dataStore.getSCL()

    def ReadTargetMemory(self, memtype: MEMTYPE, address: int, size: int, data: bytearray) -> int:
        assert self.dataStore is not None
        if self.dataStore.getDeviceFamily() == FamilyType.PIC32:
            return self.ReadTargetMemory_PIC32(memtype, address, size, data)

        if memtype == MEMTYPE.FILE_REGISTERS:
            return self.dataStore.getSFRMemory().Read(address, size, data)
        if memtype == MEMTYPE.NMMR:
            return self.dataStore.getNMMRMemory().Read(address, size, data)
        if memtype == MEMTYPE.PROGRAM_MEMORY:
            return self.dataStore.getProgMemory().Read(address, size, data)
        return 0

    def WriteTargetMemory(self, memtype: MEMTYPE, address: int, size: int, data: bytes) -> int:
        assert self.dataStore is not None
        if self.dataStore.getDeviceFamily() == FamilyType.PIC32:
            return self.WriteTargetMemory_PIC32(memtype, address, size, data)

        if memtype == MEMTYPE.FILE_REGISTERS:
            return self.dataStore.getSFRMemory().Write(address, size, data)
        if memtype == MEMTYPE.PROGRAM_MEMORY:
            return self.dataStore.getProgMemory().Write(address, size, data)
        return 0

    def ReadTargetMemory_PIC32(self, memtype: MEMTYPE, address: int, size: int, data: bytearray) -> int:
        assert self.dataStore is not None
        mems = self.dataStore.getPic32PhysicalMems()
        if memtype == MEMTYPE.FILE_REGISTERS:
            return mems.getFileMemory().Read(address, size, data)
        if memtype == MEMTYPE.PROGRAM_MEMORY:
            return mems.getProgMemory().Read(address, size, data)
        if memtype == MEMTYPE.NMMR:
            return self.dataStore.getNMMRMemory().Read(address, size, data)
        if memtype == MEMTYPE.PERIPHERAL_MEMORY:
            return mems.getPeripheralMemory().Read(address, size, data)
        return 0

    def WriteTargetMemory_PIC32(self, memtype: MEMTYPE, address: int, size: int, data: bytes) -> int:
        assert self.dataStore is not None
        mems = self.dataStore.getPic32PhysicalMems()
        if memtype == MEMTYPE.FILE_REGISTERS:
            return mems.getFileMemory().Write(address, size, data)
        if memtype == MEMTYPE.PROGRAM_MEMORY:
            return mems.getProgMemory().Write(address, size, data)
        if memtype == MEMTYPE.NMMR:
            return self.dataStore.getNMMRMemory().Write(address, size, data)
        if memtype == MEMTYPE.PERIPHERAL_MEMORY:
            return mems.getPeripheralMemory().Write(address, size, data)
        return 0

    def Attach(self, observer: Any, object: Any = None) -> bool:
        if callable(observer):
            self.observers.append(_ObserverWrapper(observer))
            return True
        self.observers.append(observer)
        return True

    def Detach(self, observer: Any, object: Any = None) -> bool:
        try:
            self.observers = [o for o in self.observers if o is not observer]
            return True
        except Exception:
            return False

    def Notify(self, obj: Any) -> None:
        for o in list(self.observers):
            try:
                o.Update(obj)
            except Exception:
                continue

    def GetStopwatchValue(self) -> int:
        assert self.processor is not None
        return self.processor.getStopwatch()

    def SupportsDebugModeRead(self) -> bool:
        return False

    def GetProjectStatusInfo(self) -> Optional[Collection[Any]]:
        return None

    def resetCodeCoverage(self) -> None:
        self.codeCoverageData.clear()

    def retrieveCodeCoverage(self) -> Dict[int, int]:
        return dict(self.codeCoverageData)

    def startCodeCoverage(self) -> None:
        self.codeCoverageEnabled = True

    def stopCodeCoverage(self) -> None:
        self.codeCoverageEnabled = False

    def resetStopwatch(self) -> None:
        # Minimal stub: stopwatch is owned by processor in full impl.
        return

    def _code_coverage(self) -> None:
        if not self.codeCoverageEnabled or self.processor is None:
            return
        for pc in self.processor.getAddressesCovered():
            self.codeCoverageData[pc] = self.codeCoverageData.get(pc, 0) + 1

    def _reset_vdd_vss_to_nominal_voltage(self) -> None:
        # Voltage/pin modeling is out of scope for this minimal port.
        return
