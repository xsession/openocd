from __future__ import annotations

import enum
import struct
from dataclasses import dataclass
from typing import ClassVar


class ActionType(enum.IntEnum):
    InvalidAction = 0
    TickClock = 1
    WriteToBus = 2  # obsolete
    ReadFromBus = 3  # obsolete
    ResetPeripheral = 4
    LogMessage = 5
    Interrupt = 6
    Disconnect = 7
    Error = 8
    OK = 9
    Handshake = 10
    PushDoubleWord = 11
    GetDoubleWord = 12
    PushWord = 13
    GetWord = 14
    PushByte = 15
    GetByte = 16
    IsHalted = 17
    RegisterGet = 18
    RegisterSet = 19
    SingleStepMode = 20
    ReadFromBusByte = 21
    ReadFromBusWord = 22
    ReadFromBusDoubleWord = 23
    ReadFromBusQuadWord = 24
    WriteToBusByte = 25
    WriteToBusWord = 26
    WriteToBusDoubleWord = 27
    WriteToBusQuadWord = 28
    PushQuadWord = 29
    GetQuadWord = 30
    PushConfirmation = 31

    Step = 100  # all custom action type numbers must not fall in this range


@dataclass(frozen=True, slots=True)
class ProtocolMessage:
    """Wire-compatible with Renode CoSimulationPlugin `ProtocolMessage`/`Protocol`.

    Layout (little-endian):
      int32 actionId
      uint64 address
      uint64 data
      int32 peripheralIndex

    Total: 24 bytes
    """

    NoPeripheralIndex: ClassVar[int] = -1
    _STRUCT: ClassVar[struct.Struct] = struct.Struct("<iQQi")

    action_id: int
    address: int
    data: int
    peripheral_index: int = NoPeripheralIndex

    def to_bytes(self) -> bytes:
        return self._STRUCT.pack(int(self.action_id), int(self.address), int(self.data), int(self.peripheral_index))

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProtocolMessage":
        if len(raw) != cls._STRUCT.size:
            raise ValueError(f"Expected {cls._STRUCT.size} bytes, got {len(raw)}")
        action_id, address, data, peripheral_index = cls._STRUCT.unpack(raw)
        return cls(action_id=action_id, address=address, data=data, peripheral_index=peripheral_index)

    @property
    def action(self) -> ActionType:
        return ActionType(int(self.action_id))
