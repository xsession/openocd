"""Simulator surface.

For now this re-exports the minimal implementation from `mchp_mdbcore.simulator`.
The long-term intent is to keep simulator-specific APIs under `mchp_simulator`.
"""

from mchp_mdbcore.simulator import (  # noqa: F401
    Simulator,
    MEMTYPE,
    ResetType,
    ToolEvent,
    SimulatorDataStoreDefault,
    FamilyType,
    Processor,
)

__all__ = [
    "Simulator",
    "MEMTYPE",
    "ResetType",
    "ToolEvent",
    "SimulatorDataStoreDefault",
    "FamilyType",
    "Processor",
]
