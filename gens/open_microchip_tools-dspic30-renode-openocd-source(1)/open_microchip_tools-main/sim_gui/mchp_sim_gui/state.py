from __future__ import annotations

from typing import List

import reflex as rx

from mchp_simulator import debug_backend


class SimState(rx.State):
    device_prefix: str = "dsPIC33"
    devices: List[str] = []
    device: str = "dsPIC33EP512GM710"

    firmware_path: str = ""
    breakpoint_addr: str = ""
    run_steps_count: str = "1000"

    mem_space: str = "program"
    mem_addr: str = "0x0"
    mem_size: str = "64"
    mem_dump: str = ""
    breakpoints_text: str = ""

    pc: str = ""
    ips: str = ""
    mem_at_pc: str = ""
    trace_text: str = ""
    firmware_loaded: bool = False

    error: str = ""

    def _apply_status(self, status) -> None:
        self.error = ""
        self.firmware_loaded = bool(status.get("firmware_loaded"))

        pc = status.get("pc")
        self.pc = "" if pc is None else f"0x{int(pc):08X}"

        ips = status.get("instructions_per_second")
        self.ips = "" if ips is None else str(ips)

        trace = status.get("trace") or []
        self.trace_text = "\n".join(
            [f"0x{t['pc']:08X}  {t['bytes_hex']}" for t in trace if "pc" in t]
        )

        if pc is not None:
            try:
                self.mem_at_pc = debug_backend.read_program(int(pc), 16)
            except Exception:
                self.mem_at_pc = ""
        else:
            self.mem_at_pc = ""

        bps = status.get("breakpoints") or []
        self.breakpoints_text = "\n".join([f"0x{int(a):08X}" for a in bps])

    def refresh_devices(self) -> None:
        self.devices = debug_backend.list_devices(self.device_prefix)[:500]
        if self.devices and self.device not in self.devices:
            self.device = self.devices[0]

    def init(self) -> None:
        try:
            self.refresh_devices()
            status = debug_backend.init_session(self.device)
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def load(self) -> None:
        try:
            status = debug_backend.load_firmware(self.firmware_path)
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def reset(self) -> None:
        try:
            status = debug_backend.reset()
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def step(self) -> None:
        try:
            status = debug_backend.step()
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def run(self) -> None:
        try:
            status = debug_backend.run(10000)
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def run_steps(self) -> None:
        try:
            n = int(self.run_steps_count.strip() or "0", 0)
            status = debug_backend.run_steps(n)
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def halt(self) -> None:
        try:
            status = debug_backend.halt()
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def add_breakpoint(self) -> None:
        try:
            addr = int(self.breakpoint_addr.strip(), 0)
            status = debug_backend.add_breakpoint(addr)
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def clear_breakpoints(self) -> None:
        try:
            status = debug_backend.clear_breakpoints()
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)

    def read_memory(self) -> None:
        try:
            addr = int(self.mem_addr.strip() or "0", 0)
            size = int(self.mem_size.strip() or "0", 0)
            self.mem_dump = debug_backend.read_memory(self.mem_space, addr, size)
        except Exception as e:
            self.error = str(e)

    def refresh(self) -> None:
        try:
            status = debug_backend.get_status()
            self._apply_status(status)
        except Exception as e:
            self.error = str(e)
