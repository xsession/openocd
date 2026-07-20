from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Field:
    name: str
    description: str
    bit_offset: int
    bit_width: int
    access: str | None = None
    enumerated_values: list[tuple[str, int, str]] = field(default_factory=list)


@dataclass(slots=True)
class Register:
    name: str
    description: str
    offset: int
    size: int
    access: str
    reset_value: int = 0
    fields: list[Field] = field(default_factory=list)


@dataclass(slots=True)
class Peripheral:
    name: str
    description: str
    base_address: int
    registers: list[Register] = field(default_factory=list)
    interrupts: list[tuple[str, int, str]] = field(default_factory=list)
    source_path: str = ""


@dataclass(slots=True)
class DeviceManifest:
    id: str
    name: str
    vendor: str
    family: str
    source: str
    output: Path
    core: str
    address_unit_bits: int = 8
    width: int = 32
    address_scale: int = 1
    default_register_width: int = 32
    device_xml_patterns: list[str] = field(default_factory=list)
    include_tokens: list[str] = field(default_factory=list)
    exclude_tokens: list[str] = field(default_factory=list)
    cortex_debug: bool = False
    processor_name: str = ""
    compatibility_note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
