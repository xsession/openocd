from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .device_catalog import DeviceSpec, available_device_names, guess_device_spec
from .firmware_image import FirmwareImage
from .firmware_simulator import FirmwareSimulator


class BackendError(RuntimeError):
    pass


_session: Optional[FirmwareSimulator] = None
_session_device: Optional[DeviceSpec] = None
_session_firmware: Optional[FirmwareImage] = None


def list_devices(prefix: str = "") -> List[str]:
    names = available_device_names()
    if prefix:
        p = prefix.lower()
        names = [n for n in names if n.lower().startswith(p)]
    return names


def init_session(device_name: str) -> Dict[str, Any]:
    global _session, _session_device, _session_firmware

    _session_device = guess_device_spec(device_name)
    _session = FirmwareSimulator(_session_device)
    _session.Engage(None)
    _session_firmware = None
    return get_status()


def load_firmware(path: str) -> Dict[str, Any]:
    global _session_firmware
    if _session is None:
        raise BackendError("Session not initialized")

    img = FirmwareImage.from_path(path)
    _session.load_firmware(img)
    _session_firmware = img
    return get_status()


def reset() -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.ResetTarget()
    return get_status()


def halt() -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.HaltTarget()
    return get_status()


def step() -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.SingleStepTarget()
    return get_status()


def run_steps(steps: int = 1000) -> Dict[str, Any]:
    """Step up to N instructions, stopping early if a breakpoint halts."""

    if _session is None:
        raise BackendError("Session not initialized")

    n = max(0, int(steps))
    for _ in range(n):
        cont = _session.SingleStepTarget()
        if cont is False:
            break
    return get_status()


def run(max_steps: int = 10000) -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.RunTarget(max_steps=max_steps)
    return get_status()


def add_breakpoint(address: int) -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.set_breakpoint(int(address))
    return get_status()


def clear_breakpoints() -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.clear_breakpoints()
    return get_status()


def list_breakpoints() -> List[int]:
    if _session is None:
        raise BackendError("Session not initialized")
    return _session.get_breakpoints()


def set_pc(address: int) -> Dict[str, Any]:
    if _session is None:
        raise BackendError("Session not initialized")
    _session.SetPC(int(address))
    return get_status()


def read_program(address: int, size: int = 16) -> str:
    if _session is None or _session.dataStore is None:
        raise BackendError("Session not initialized")

    a = int(address)
    n = max(0, int(size))
    buf = bytearray(n)
    _session.dataStore.getProgMemory().Read(a, n, buf)
    return buf.hex().upper()


def read_memory(space: str, address: int, size: int = 16) -> str:
    """Read memory by space name.

    Supported spaces: program, sfr, nmmr, file, peripheral
    """

    if _session is None or _session.dataStore is None:
        raise BackendError("Session not initialized")

    sp = (space or "").strip().lower()
    a = int(address)
    n = max(0, int(size))
    buf = bytearray(n)

    ds = _session.dataStore

    if sp == "program":
        ds.getProgMemory().Read(a, n, buf)
    elif sp == "sfr":
        ds.getSFRMemory().Read(a, n, buf)
    elif sp == "nmmr":
        ds.getNMMRMemory().Read(a, n, buf)
    elif sp == "file":
        # For non-PIC32, map file to SFR-backed storage.
        try:
            ds.getFileMemory().Read(a, n, buf)
        except Exception:
            ds.getSFRMemory().Read(a, n, buf)
    elif sp == "peripheral":
        try:
            ds.getPic32PhysicalMems().getPeripheralMemory().Read(a, n, buf)
        except Exception:
            # Not available for most non-PIC32 models.
            return ""
    else:
        raise BackendError(f"Unknown memory space: {space}")

    return buf.hex().upper()


def get_status(trace_limit: int = 200) -> Dict[str, Any]:
    pc = None
    ips = None
    trace: List[Dict[str, Any]] = []

    if _session is not None and _session.processor is not None:
        try:
            pc = _session.GetPC()
        except Exception:
            pc = None
        ips = _session.getInstructionsPerSecond()
        trace = [asdict(t) for t in _session.get_trace(limit=trace_limit)]

    return {
        "device": None if _session_device is None else asdict(_session_device),
        "pc": pc,
        "instructions_per_second": ips,
        "trace": trace,
        "breakpoints": [] if _session is None else _session.get_breakpoints(),
        "firmware_loaded": _session_firmware is not None,
    }
