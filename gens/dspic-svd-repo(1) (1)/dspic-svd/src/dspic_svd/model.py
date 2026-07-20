from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EnumValue:
    name: str
    value: int
    description: str = ""


@dataclass(slots=True)
class Field:
    name: str
    mask: int
    description: str = ""
    access: str | None = None
    enums: list[EnumValue] = field(default_factory=list)

    @property
    def bit_offset(self) -> int:
        if self.mask == 0:
            return 0
        return (self.mask & -self.mask).bit_length() - 1

    @property
    def bit_width(self) -> int:
        shifted = self.mask >> self.bit_offset
        width = 0
        while shifted & 1:
            width += 1
            shifted >>= 1
        return width or self.mask.bit_count()


@dataclass(slots=True)
class Register:
    name: str
    address: int
    size: int
    description: str = ""
    access: str = "read-write"
    reset_value: int = 0
    reset_mask: int | None = None
    fields: list[Field] = field(default_factory=list)


@dataclass(slots=True)
class Interrupt:
    name: str
    value: int
    description: str = ""


@dataclass(slots=True)
class Device:
    name: str
    description: str
    registers: list[Register]
    interrupts: list[Interrupt] = field(default_factory=list)
    vendor: str = "Microchip"
    address_unit_bits: int = 8
    width: int = 16
