"""Clean-room Python reimplementation of selected MPLAB simulator surfaces.

This package intentionally focuses on tool-facing APIs (e.g. `Simulator`) and uses
lazy stub modules for the very large Java simulator class tree.
"""

from .simulator import (
    Simulator,
    MEMTYPE,
    ResetType,
    ToolEvent,
    SimulatorDataStoreDefault,
    FamilyType,
    Processor,
)
from .simulator_exception import SimulatorException
from .processor_api import ProcessorAPI
from .device_catalog import DeviceSpec, available_devices, available_device_names, guess_device_spec
from .firmware_image import FirmwareImage, Segment
from .firmware_simulator import FirmwareSimulator, TraceEntry

__all__ = [
    "Simulator",
    "MEMTYPE",
    "ResetType",
    "ToolEvent",
    "SimulatorDataStoreDefault",
    "FamilyType",
    "Processor",
    "SimulatorException",
    "ProcessorAPI",
    "DeviceSpec",
    "available_devices",
    "available_device_names",
    "guess_device_spec",
    "FirmwareImage",
    "Segment",
    "FirmwareSimulator",
    "TraceEntry",
]
