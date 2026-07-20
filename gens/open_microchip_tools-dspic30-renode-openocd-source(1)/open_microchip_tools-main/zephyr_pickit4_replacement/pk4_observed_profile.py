from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


PK4_FAMILY = "ARM_MPU"
PK4_PROFILE_NAME = "PK4_OBSERVED_DUAL_APP_LAYOUT"
PK4_ARCHITECTURE = "arm-cortex-m"
PK4_BOOT_BASE = 0x00400000
PK4_APP_BASE = 0x0040C000
PK4_APP2_BASE = 0x00500000
PK4_INITIAL_SP = 0x20449460
PK4_RESET_VECTOR = 0x0040E8AD
PK4_APP2_INITIAL_SP = 0x2040A910
PK4_APP2_RESET_VECTOR = 0x00504189
PK4_BOOT_WINDOW_SIZE = 48 * 1024
PK4_APP_WINDOW_SIZE = 64 * 1024
PK4_APP2_WINDOW_SIZE = 160 * 1024
PK4_PRIMARY_ROLE = "RI4 host-facing app slot"
PK4_SECONDARY_ROLE = "CMSIS-DAP control/update slot"
PK4_SECONDARY_IDENTITY = "MPLAB PICkit 4 CMSIS-DAP"


@dataclass
class Pk4ObservedProbeModel:
    debug_mode: bool = False
    halted: bool = False
    pc: int = PK4_RESET_VECTOR
    boot_flash: bytearray = field(default_factory=lambda: bytearray(b"\xFF" * PK4_BOOT_WINDOW_SIZE))
    app_flash: bytearray = field(default_factory=lambda: bytearray(b"\xFF" * PK4_APP_WINDOW_SIZE))
    app2_flash: bytearray = field(default_factory=lambda: bytearray(b"\xFF" * PK4_APP2_WINDOW_SIZE))
    last_program_region: str = "none"
    last_program_role: str = "unknown"

    def region_role(self, region: str) -> str:
        if region == "boot":
            return "boot strap slot"
        if region == "app":
            return PK4_PRIMARY_ROLE
        if region == "app2":
            return PK4_SECONDARY_ROLE
        return "unknown"

    def execution_slot(self) -> str:
        if PK4_BOOT_BASE <= self.pc < (PK4_BOOT_BASE + PK4_BOOT_WINDOW_SIZE):
            return "boot"
        if PK4_APP_BASE <= self.pc < (PK4_APP_BASE + PK4_APP_WINDOW_SIZE):
            return "app"
        if PK4_APP2_BASE <= self.pc < (PK4_APP2_BASE + PK4_APP2_WINDOW_SIZE):
            return "app2"
        return "external"

    def erase_chip(self) -> None:
        self.boot_flash[:] = b"\xFF" * len(self.boot_flash)
        self.app_flash[:] = b"\xFF" * len(self.app_flash)
        self.app2_flash[:] = b"\xFF" * len(self.app2_flash)
        self.last_program_region = "chip-erase"
        self.last_program_role = "unknown"

    def classify_address(self, address: int, size: int = 0) -> Tuple[str, int]:
        if PK4_BOOT_BASE <= address < (PK4_BOOT_BASE + PK4_BOOT_WINDOW_SIZE):
            offset = address - PK4_BOOT_BASE
            if offset + size > PK4_BOOT_WINDOW_SIZE:
                raise ValueError("boot window overflow")
            return ("boot", offset)
        if PK4_APP_BASE <= address < (PK4_APP_BASE + PK4_APP_WINDOW_SIZE):
            offset = address - PK4_APP_BASE
            if offset + size > PK4_APP_WINDOW_SIZE:
                raise ValueError("app window overflow")
            return ("app", offset)
        if PK4_APP2_BASE <= address < (PK4_APP2_BASE + PK4_APP2_WINDOW_SIZE):
            offset = address - PK4_APP2_BASE
            if offset + size > PK4_APP2_WINDOW_SIZE:
                raise ValueError("app2 window overflow")
            return ("app2", offset)
        if 0 <= address < PK4_APP_WINDOW_SIZE:
            if address + size > PK4_APP_WINDOW_SIZE:
                raise ValueError("relative app window overflow")
            return ("app", address)
        raise ValueError(f"address خارج modeled windows: 0x{address:08X}")

    def write_program(self, address: int, data: bytes) -> Dict[str, int | str]:
        region, offset = self.classify_address(address, len(data))
        target = self.boot_flash if region == "boot" else self.app_flash if region == "app" else self.app2_flash
        target[offset : offset + len(data)] = data
        self.last_program_region = region
        self.last_program_role = self.region_role(region)
        return {
            "region": region,
            "absoluteAddress": PK4_BOOT_BASE + offset if region == "boot" else PK4_APP_BASE + offset if region == "app" else PK4_APP2_BASE + offset,
            "offset": offset,
            "size": len(data),
        }

    def read_program(self, address: int, size: int) -> Dict[str, int | str | bytes]:
        region, offset = self.classify_address(address, size)
        source = self.boot_flash if region == "boot" else self.app_flash if region == "app" else self.app2_flash
        self.last_program_region = region
        self.last_program_role = self.region_role(region)
        return {
            "region": region,
            "absoluteAddress": PK4_BOOT_BASE + offset if region == "boot" else PK4_APP_BASE + offset if region == "app" else PK4_APP2_BASE + offset,
            "offset": offset,
            "size": size,
            "data": bytes(source[offset : offset + size]),
        }

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
            return PK4_FAMILY
        if normalized == "probe profile":
            return PK4_PROFILE_NAME
        if normalized == "boot base":
            return f"0x{PK4_BOOT_BASE:08X}"
        if normalized == "app base":
            return f"0x{PK4_APP_BASE:08X}"
        if normalized == "app2 base":
            return f"0x{PK4_APP2_BASE:08X}"
        if normalized == "reset vector":
            return f"0x{PK4_RESET_VECTOR:08X}"
        if normalized == "app2 reset vector":
            return f"0x{PK4_APP2_RESET_VECTOR:08X}"
        if normalized == "initial sp":
            return f"0x{PK4_INITIAL_SP:08X}"
        if normalized == "app2 initial sp":
            return f"0x{PK4_APP2_INITIAL_SP:08X}"
        if normalized == "boot window size":
            return f"0x{PK4_BOOT_WINDOW_SIZE:X}"
        if normalized == "app window size":
            return f"0x{PK4_APP_WINDOW_SIZE:X}"
        if normalized == "app2 window size":
            return f"0x{PK4_APP2_WINDOW_SIZE:X}"
        if normalized == "primary role":
            return PK4_PRIMARY_ROLE
        if normalized == "secondary role":
            return PK4_SECONDARY_ROLE
        if normalized == "secondary identity":
            return PK4_SECONDARY_IDENTITY
        if normalized == "execution slot":
            return self.execution_slot()
        if normalized == "execution role":
            return self.region_role(self.execution_slot())
        if normalized == "last program region":
            return self.last_program_region
        if normalized == "last program role":
            return self.last_program_role
        if normalized == "architecture":
            return PK4_ARCHITECTURE
        return "unsupported"

    def status_snapshot(self, keys: Iterable[str]) -> Dict[str, str]:
        return {key: self.get_status_value(key) for key in keys}


DEFAULT_STATUS_KEYS: List[str] = [
    "Commands in progress",
    "Debug Mode",
    "Target Halted",
    "Program Counter",
    "Family",
    "Probe Profile",
    "Boot Base",
    "App Base",
    "App2 Base",
    "Reset Vector",
    "Initial SP",
    "App2 Reset Vector",
    "App2 Initial SP",
    "Boot Window Size",
    "App Window Size",
    "App2 Window Size",
    "Primary Role",
    "Secondary Role",
    "Secondary Identity",
    "Execution Slot",
    "Execution Role",
    "Last Program Region",
    "Last Program Role",
    "Architecture",
]