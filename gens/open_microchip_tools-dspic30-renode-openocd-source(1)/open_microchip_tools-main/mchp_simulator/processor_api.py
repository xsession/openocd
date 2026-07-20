from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol


class ProcessorAPI:
    class ResetType(Enum):
        MCLR = "MCLR"
        POR = "POR"

    class ProcessorObserver(Protocol):
        class ProcessorEvent(Enum):
            INTERRUPT_OCCURRED = "INTERRUPT_OCCURRED"
            WAKEUP = "WAKEUP"
            POWER_SAVE_ENTERED = "POWER_SAVE_ENTERED"
            PC_WRAPPED = "PC_WRAPPED"
            RESET_INSTRUCTION = "RESET_INSTRUCTION"
            RESET_MCLR = "RESET_MCLR"
            RESET_POR = "RESET_POR"
            WATCHDOG_TIMER_CLEARED = "WATCHDOG_TIMER_CLEARED"
            WATCHDOG_TIMER_EXPIRED = "WATCHDOG_TIMER_EXPIRED"
            STACK_ERROR = "STACK_ERROR"
            SESSION_PROGRAM = "SESSION_PROGRAM"
            SESSION_START = "SESSION_START"
            SESSION_END = "SESSION_END"
            PERIPH_BUS_RW = "PERIPH_BUS_RW"
            PANEL_SWAP = "PANEL_SWAP"
            SECURE_STATE_CHANGE = "SECURE_STATE_CHANGE"

        def notify(self, event: "ProcessorAPI.ProcessorObserver.ProcessorEvent", obj: Any) -> None:
            ...


__all__ = ["ProcessorAPI"]
