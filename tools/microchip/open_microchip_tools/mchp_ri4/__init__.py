"""Clean-room Python reimplementation of RI4 USB comm surfaces.

This package focuses on the RI4 side/data channel framing used by tools like
PICkit 4 and ICD 4/5.
"""

from .errors import Ri4Error, Ri4ProtocolError, Ri4TransportError
from .ri4_com import ComChannel, Ri4Com
from .icd4_comms_usb import ICD4CommsUsb
from .commands import Commands
from .script import Script
from .device_file import DeviceFile, DeviceFileSAXReader
from .family_profiles import FamilyProfile, FAMILY_PROFILES, JAVA_DEVICE_FAMILIES, family_inventory, get_family_profile
from .named_session import NamedScriptSession
from .power_control import PowerStatus, Ri4PowerController, parse_power_status_payload

_JAVA_KNOWLEDGE_EXPORTS = {
    "ScriptInvocation",
    "RawCommandInvocation",
    "JavaMethodKnowledge",
    "JavaClassKnowledge",
    "JavaFamilyKnowledge",
    "JavaRi4KnowledgeBase",
    "load_java_ri4_knowledge",
    "dump_java_ri4_knowledge",
}

_FIRMWARE_UPDATE_EXPORTS = {
    "ToolFirmwareState",
    "assess_firmware_state",
    "probe_tool_firmware",
}


def __getattr__(name):
    if name in _JAVA_KNOWLEDGE_EXPORTS:
        from . import java_knowledge

        return getattr(java_knowledge, name)
    if name in _FIRMWARE_UPDATE_EXPORTS:
        from . import firmware_update

        return getattr(firmware_update, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Ri4Error",
    "Ri4ProtocolError",
    "Ri4TransportError",
    "ComChannel",
    "Ri4Com",
    "ICD4CommsUsb",
    "Commands",
    "Script",
    "DeviceFile",
    "DeviceFileSAXReader",
    "FamilyProfile",
    "FAMILY_PROFILES",
    "JAVA_DEVICE_FAMILIES",
    "family_inventory",
    "get_family_profile",
    "PowerStatus",
    "Ri4PowerController",
    "parse_power_status_payload",
    "ToolFirmwareState",
    "assess_firmware_state",
    "probe_tool_firmware",
    "ScriptInvocation",
    "RawCommandInvocation",
    "JavaMethodKnowledge",
    "JavaClassKnowledge",
    "JavaFamilyKnowledge",
    "JavaRi4KnowledgeBase",
    "load_java_ri4_knowledge",
    "dump_java_ri4_knowledge",
    "NamedScriptSession",
]
