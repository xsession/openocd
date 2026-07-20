from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .java_knowledge import load_java_ri4_knowledge


@dataclass(frozen=True)
class FamilyProfile:
    family: str
    programmer_class: str
    debugger_class: str
    behavior: str
    max_read_chunk_size: int = 0
    fixed_read_window_size: int = 0
    program_data_width: int = 1
    program_address_increment: int = 1
    program_entry_scripts: Tuple[str, ...] = ()
    program_exit_scripts: Tuple[str, ...] = ()
    erase_scripts: Tuple[str, ...] = ("EraseChip",)
    write_program_scripts: Tuple[str, ...] = ("WriteProgmem",)
    read_program_scripts: Tuple[str, ...] = ("ReadProgmem",)
    write_config_scripts: Tuple[str, ...] = ("WriteConfigmem",)
    read_config_scripts: Tuple[str, ...] = ("ReadConfigmem",)
    enter_debug_scripts: Tuple[str, ...] = ("EnterDebugMode",)
    get_pc_scripts: Tuple[str, ...] = ("GetPC",)
    set_pc_scripts: Tuple[str, ...] = ("SetPC",)
    run_scripts: Tuple[str, ...] = ("Run",)
    step_scripts: Tuple[str, ...] = ("SingleStep", "SingleStepUFEX")
    halt_scripts: Tuple[str, ...] = ("Halt",)
    halt_status_scripts: Tuple[str, ...] = ("GetHaltStatus",)
    post_halt_scripts: Tuple[str, ...] = ("PostHalt",)
    set_hw_breakpoint_scripts: Tuple[str, ...] = ("SetHWBP",)
    set_data_breakpoint_scripts: Tuple[str, ...] = ("SetDataHWBP",)
    clear_hw_breakpoint_scripts: Tuple[str, ...] = ("ClearHWBP",)
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "family": self.family,
            "programmerClass": self.programmer_class,
            "debuggerClass": self.debugger_class,
            "behavior": self.behavior,
            "maxReadChunkSize": self.max_read_chunk_size,
            "fixedReadWindowSize": self.fixed_read_window_size,
            "programDataWidth": self.program_data_width,
            "programAddressIncrement": self.program_address_increment,
            "programEntryScripts": list(self.program_entry_scripts),
            "programExitScripts": list(self.program_exit_scripts),
            "eraseScripts": list(self.erase_scripts),
            "writeProgramScripts": list(self.write_program_scripts),
            "readProgramScripts": list(self.read_program_scripts),
            "writeConfigScripts": list(self.write_config_scripts),
            "readConfigScripts": list(self.read_config_scripts),
            "enterDebugScripts": list(self.enter_debug_scripts),
            "getPcScripts": list(self.get_pc_scripts),
            "setPcScripts": list(self.set_pc_scripts),
            "runScripts": list(self.run_scripts),
            "stepScripts": list(self.step_scripts),
            "haltScripts": list(self.halt_scripts),
            "haltStatusScripts": list(self.halt_status_scripts),
            "postHaltScripts": list(self.post_halt_scripts),
            "setHardwareBreakpointScripts": list(self.set_hw_breakpoint_scripts),
            "setDataBreakpointScripts": list(self.set_data_breakpoint_scripts),
            "clearHardwareBreakpointScripts": list(self.clear_hw_breakpoint_scripts),
            "notes": self.notes,
        }


def _tuple(*items: str) -> Tuple[str, ...]:
    return tuple(items)


BEHAVIOR_TEMPLATES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "pic18_tmod": {
        "program_entry_scripts": _tuple("EnterTMOD_LV", "EnterTMOD_VPPFirst", "EnterTMOD_HV"),
        "program_exit_scripts": _tuple("ExitTMOD",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange"),
        "write_program_scripts": _tuple("WriteProgmem",),
        "read_program_scripts": _tuple("ReadProgmem", "ReadProgmemDE"),
        "write_config_scripts": _tuple("WriteConfigmem", "WriteOtpConfigmem"),
        "read_config_scripts": _tuple("ReadConfigmem",),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "pic16_enhanced": {
        "program_entry_scripts": _tuple("EnterTMOD_LV", "EnterTMOD_VPPFirst", "EnterTMOD_HV"),
        "program_exit_scripts": _tuple("ExitTMOD",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange", "EraseTestmemRange", "EraseDataEEmemRange", "EraseDataEEmem"),
        "write_program_scripts": _tuple("WriteProgmem", "WriteConfigmemDE", "WriteTestmem"),
        "read_program_scripts": _tuple("ReadProgmem", "ReadProgmemDE", "ReadTestmem"),
        "write_config_scripts": _tuple("WriteConfigmem", "WriteConfigmemDE", "WriteOtpConfigmem"),
        "read_config_scripts": _tuple("ReadConfigmem", "ReadTestmem"),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "dspic_pe": {
        "program_entry_scripts": _tuple("EnterTMOD_LV", "EnterTMOD_HV", "EnterTMOD_PE"),
        "program_exit_scripts": _tuple("ExitTMOD",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange", "EraseDataEEmemRange"),
        "write_program_scripts": _tuple("WriteProgmemPE", "WriteProgmem", "WriteProgmemDE"),
        "read_program_scripts": _tuple("ReadProgmemPE", "ReadProgmem", "ReadProgmemDE"),
        "write_config_scripts": _tuple("WriteConfigmem",),
        "read_config_scripts": _tuple("ReadConfigmem",),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "dspic_de": {
        "program_entry_scripts": _tuple("EnterTMOD_LV", "EnterTMOD_HV"),
        "program_exit_scripts": _tuple("ExitTMOD",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange"),
        "write_program_scripts": _tuple("WriteProgmemDE", "WriteProgmem"),
        "read_program_scripts": _tuple("ReadProgmemDE", "ReadProgmem"),
        "write_config_scripts": _tuple("WriteConfigmem",),
        "read_config_scripts": _tuple("ReadConfigmem",),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "pic32_pe": {
        "program_entry_scripts": _tuple("EnterTMOD_LV", "InitJTAG", "SetupSerialMode", "LoadLoader", "DownloadPE", "TestPEConnect"),
        "program_exit_scripts": _tuple("ExitTMOD",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRangePE", "EraseProgmemRange"),
        "write_program_scripts": _tuple("WriteProgmemPE", "P32PE_ProgramCluster", "WriteProgmemDE"),
        "read_program_scripts": _tuple("ReadProgmemPE", "ReadRAM"),
        "write_config_scripts": _tuple("WriteConfigmemPE", "WriteConfigmem"),
        "read_config_scripts": _tuple("ReadConfigmem", "ReadProgmemPE"),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "arm_flashless": {
        "program_entry_scripts": _tuple(),
        "program_exit_scripts": _tuple(),
        "erase_scripts": _tuple(),
        "write_program_scripts": _tuple("WriteProgmem", "WriteRAM"),
        "read_program_scripts": _tuple("ReadProgmem", "ReadRAM"),
        "write_config_scripts": _tuple("WriteConfigmem",),
        "read_config_scripts": _tuple("ReadConfigmem",),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "arm_efc": {
        "program_entry_scripts": _tuple(),
        "program_exit_scripts": _tuple(),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange"),
        "write_program_scripts": _tuple("WriteProgmemPE", "WriteProgmem", "WriteBootMem"),
        "read_program_scripts": _tuple("ReadProgmemPE", "ReadProgmem", "ReadEmu"),
        "write_config_scripts": _tuple("WriteConfigmem",),
        "read_config_scripts": _tuple("ReadConfigmem",),
        "enter_debug_scripts": _tuple("EnterDebugMode",),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
    "avr_progmode": {
        "program_entry_scripts": _tuple("EnterProgModeHvSp", "EnterProgModeHvSpRst", "EnterProgModeHvUpt", "EnterProgMode"),
        "program_exit_scripts": _tuple("ExitProgMode",),
        "erase_scripts": _tuple("EraseChip", "EraseProgmemRange", "EraseOcdProgmemPreOne", "EraseOcdProgmemPreTwo"),
        "write_program_scripts": _tuple("WriteProgmem", "WriteBootMem", "WriteOcdProgmem"),
        "read_program_scripts": _tuple("ReadProgmem", "ReadOcdProgmem"),
        "write_config_scripts": _tuple("WriteConfigmem",),
        "read_config_scripts": _tuple("ReadConfigmemFuse", "ReadConfigmemLock", "ReadConfigmem"),
        "enter_debug_scripts": _tuple("EnterDebugModeHvSp", "EnterDebugModeHvSpRst", "EnterDebugModeHvUpt", "EnterDebugMode"),
        "get_pc_scripts": _tuple("GetPC",),
        "set_pc_scripts": _tuple("SetPC",),
        "run_scripts": _tuple("Run",),
        "step_scripts": _tuple("SingleStep", "SingleStepUFEX"),
        "halt_scripts": _tuple("Halt",),
    },
}


FAMILY_BEHAVIORS: Dict[str, str] = {
    "HCS": "pic18_tmod",
    "PIC18": "pic18_tmod",
    "PIC18J": "pic18_tmod",
    "PIC16Enhanced": "pic16_enhanced",
    "PIC16": "pic16_enhanced",
    "BASELINE": "pic16_enhanced",
    "PIC18FEnhanced": "pic16_enhanced",
    "PIC18FEnhanced_V2": "pic16_enhanced",
    "PIC24FJ": "dspic_pe",
    "DSPIC30F": "dspic_pe",
    "DSPIC33FJ": "dspic_pe",
    "DSPIC33EP": "dspic_pe",
    "DSPIC30F_SMPS": "dspic_pe",
    "DSPIC33A": "dspic_de",
    "PIC32MZ": "pic32_pe",
    "PIC32MX_JTAG_ONLY": "pic32_pe",
    "PIC32MX_SSM": "pic32_pe",
    "PIC32MZ_FLASHLESS": "pic32_pe",
    "PIC32_MEC": "pic32_pe",
    "ARM_MPU": "arm_flashless",
    "EFC_6450": "arm_efc",
    "CPG": "arm_efc",
    "NVMCTRL_U2207": "arm_efc",
    "DSU_U2810": "arm_efc",
    "NVMCTRL_U2409": "arm_efc",
    "NVMCTRL_U2409_PIC32CX_BZ2": "arm_efc",
    "NVMCTRL_U2409_PIC32CX_V2": "arm_efc",
    "AVR": "avr_progmode",
}


FAMILY_NOTES: Dict[str, str] = {
    "DSPIC30F": "Java debugger writes PC via file registers rather than SetPC script.",
    "DSPIC33FJ": "Java debugger writes PC via file registers rather than SetPC script.",
    "DSPIC33A": "Prefers DE-flavored program memory access even outside simulator/debug mode.",
    "PIC18FEnhanced_V2": "Debugger uses DE-flavored program-memory helpers for breakpoints and reads.",
    "PIC32MZ": "Programming is PE-first and modeled from the Java PE entry flow.",
    "ARM_MPU": "Flashless ARM path is mostly RAM/debug oriented in Java.",
    "AVR": "AVR programming/debug entry depends on physical activation; registry keeps all Java-known script names in priority order.",
}


FAMILY_FIELD_OVERRIDES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "DSPIC30F": {"set_pc_scripts": _tuple()},
    "DSPIC33FJ": {"set_pc_scripts": _tuple()},
    "DSPIC30F_SMPS": {"set_pc_scripts": _tuple()},
    "PIC32MZ_FLASHLESS": {"write_program_scripts": _tuple("WriteProgmemPE",)},
    "PIC32_MEC": {"write_program_scripts": _tuple("WriteProgmemPE",)},
}


FAMILY_READ_CHUNK_LIMITS: Dict[str, int] = {
    "DSPIC30F": 60,
}


FAMILY_FIXED_READ_WINDOWS: Dict[str, int] = {
    "DSPIC30F": 60,
}


FAMILY_PROGRAM_MEMORY_GEOMETRY: Dict[str, Tuple[int, int]] = {
    "DSPIC30F": (3, 2),
}


PROFILE_FIELDS: Tuple[str, ...] = (
    "program_entry_scripts",
    "program_exit_scripts",
    "erase_scripts",
    "write_program_scripts",
    "read_program_scripts",
    "write_config_scripts",
    "read_config_scripts",
    "enter_debug_scripts",
    "get_pc_scripts",
    "set_pc_scripts",
    "run_scripts",
    "step_scripts",
    "halt_scripts",
)


def _known_families():
    return load_java_ri4_knowledge().families


JAVA_DEVICE_FAMILIES: Tuple[str, ...] = tuple(family.family for family in _known_families())


def _filter_candidates(available: Tuple[str, ...], preferred: Tuple[str, ...]) -> Tuple[str, ...]:
    available_set = set(available)
    return tuple(name for name in preferred if name in available_set)


def _build_family_profile(family_knowledge) -> FamilyProfile:
    behavior = FAMILY_BEHAVIORS[family_knowledge.family]
    template = BEHAVIOR_TEMPLATES[behavior]
    available_scripts = family_knowledge.all_script_names()
    overrides = FAMILY_FIELD_OVERRIDES.get(family_knowledge.family, {})
    profile_kwargs = {
        field_name: overrides.get(field_name, _filter_candidates(available_scripts, template[field_name]))
        for field_name in PROFILE_FIELDS
    }
    return FamilyProfile(
        family=family_knowledge.family,
        programmer_class=family_knowledge.programmer_class,
        debugger_class=family_knowledge.debugger_class,
        behavior=behavior,
        max_read_chunk_size=FAMILY_READ_CHUNK_LIMITS.get(family_knowledge.family, 0),
        fixed_read_window_size=FAMILY_FIXED_READ_WINDOWS.get(family_knowledge.family, 0),
        program_data_width=FAMILY_PROGRAM_MEMORY_GEOMETRY.get(family_knowledge.family, (1, 1))[0],
        program_address_increment=FAMILY_PROGRAM_MEMORY_GEOMETRY.get(family_knowledge.family, (1, 1))[1],
        halt_status_scripts=_filter_candidates(available_scripts, ("GetHaltStatus",)),
        post_halt_scripts=_filter_candidates(available_scripts, ("PostHalt",)),
        set_hw_breakpoint_scripts=_filter_candidates(available_scripts, ("SetHWBP",)),
        set_data_breakpoint_scripts=_filter_candidates(available_scripts, ("SetDataHWBP",)),
        clear_hw_breakpoint_scripts=_filter_candidates(available_scripts, ("ClearHWBP",)),
        notes=FAMILY_NOTES.get(family_knowledge.family, ""),
        **profile_kwargs,
    )


FAMILY_PROFILES: Dict[str, FamilyProfile] = {
    family_knowledge.family: _build_family_profile(family_knowledge) for family_knowledge in _known_families()
}

FAMILY_PROFILES_BY_NAME: Dict[str, FamilyProfile] = {name.upper(): profile for name, profile in FAMILY_PROFILES.items()}


def get_family_profile(family: Optional[str]) -> Optional[FamilyProfile]:
    if family is None:
        return None
    return FAMILY_PROFILES_BY_NAME.get(family.strip().upper())


def iter_family_profiles() -> Iterable[FamilyProfile]:
    for family in JAVA_DEVICE_FAMILIES:
        profile = FAMILY_PROFILES.get(family)
        if profile is None:
            raise KeyError(f"Missing family profile for {family}")
        yield profile


def _normalize_capabilities(capabilities: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not capabilities:
        return ()
    ordered: List[str] = []
    seen = set()
    for item in capabilities:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _normalize_terms(items: Optional[Sequence[str]]) -> Tuple[str, ...]:
    return _normalize_capabilities(items)


def _matches_required(available: set[str], required: Tuple[str, ...], match: str) -> bool:
    if not required:
        return True
    mode = match.strip().lower() if match else "any"
    if mode == "all":
        return all(item in available for item in required)
    return any(item in available for item in required)


def _entry_values(entry: Dict[str, object], programmer_key: str, debugger_key: str) -> set[str]:
    return set(entry.get(programmer_key, [])) | set(entry.get(debugger_key, []))


def _matches_search_prefix(entry: Dict[str, object], search_prefix: str) -> bool:
    if not search_prefix:
        return True
    prefix = search_prefix.strip().lower()
    if not prefix:
        return True
    candidates = (
        str(entry.get("family") or ""),
        str(entry.get("programmerClass") or ""),
        str(entry.get("debuggerClass") or ""),
    )
    return any(candidate.lower().startswith(prefix) for candidate in candidates if candidate)


def family_inventory(
    *,
    required_capabilities: Optional[Sequence[str]] = None,
    capability_match: str = "any",
    required_signatures: Optional[Sequence[str]] = None,
    signature_match: str = "any",
    required_groups: Optional[Sequence[str]] = None,
    group_match: str = "any",
    search_prefix: str = "",
) -> List[Dict[str, object]]:
    knowledge_by_family = {family.family: family for family in _known_families()}
    items: List[Dict[str, object]] = []
    normalized_capabilities = _normalize_capabilities(required_capabilities)
    normalized_signatures = _normalize_terms(required_signatures)
    normalized_groups = _normalize_terms(required_groups)
    for profile in iter_family_profiles():
        family_knowledge = knowledge_by_family[profile.family]
        entry = profile.to_dict()
        entry.update(
            {
                "programmerLineage": list(family_knowledge.programmer_lineage),
                "debuggerLineage": list(family_knowledge.debugger_lineage),
                "programmerScripts": list(family_knowledge.programmer_scripts),
                "debuggerScripts": list(family_knowledge.debugger_scripts),
                "programmerRawCommands": list(family_knowledge.programmer_raw_commands),
                "debuggerRawCommands": list(family_knowledge.debugger_raw_commands),
                "programmerRawCommandTags": list(family_knowledge.programmer_raw_command_tags),
                "debuggerRawCommandTags": list(family_knowledge.debugger_raw_command_tags),
                "programmerRawCommandGroups": list(family_knowledge.programmer_raw_command_groups),
                "debuggerRawCommandGroups": list(family_knowledge.debugger_raw_command_groups),
                "programmerRawCommandCapabilities": list(family_knowledge.programmer_raw_command_capabilities),
                "debuggerRawCommandCapabilities": list(family_knowledge.debugger_raw_command_capabilities),
                "programmerRawCommandSignatures": list(family_knowledge.programmer_raw_command_signatures),
                "debuggerRawCommandSignatures": list(family_knowledge.debugger_raw_command_signatures),
                "namedScriptCount": len(family_knowledge.all_script_names()),
                "supportsProgramming": bool(profile.erase_scripts or profile.write_program_scripts or profile.read_program_scripts),
                "supportsDebugging": bool(profile.enter_debug_scripts or profile.get_pc_scripts or profile.run_scripts or profile.halt_scripts),
                "supportsSetPc": bool(profile.set_pc_scripts),
                "supportsTargetPolling": bool(profile.halt_status_scripts),
                "supportsHardwareBreakpoints": bool(
                    profile.set_hw_breakpoint_scripts and profile.clear_hw_breakpoint_scripts
                ),
                "supportsWatchpoints": bool(
                    profile.set_data_breakpoint_scripts and profile.clear_hw_breakpoint_scripts
                ),
            }
        )
        if not _matches_required(
            _entry_values(entry, "programmerRawCommandCapabilities", "debuggerRawCommandCapabilities"),
            normalized_capabilities,
            capability_match,
        ):
            continue
        if not _matches_required(
            _entry_values(entry, "programmerRawCommandSignatures", "debuggerRawCommandSignatures"),
            normalized_signatures,
            signature_match,
        ):
            continue
        if not _matches_required(
            _entry_values(entry, "programmerRawCommandGroups", "debuggerRawCommandGroups"),
            normalized_groups,
            group_match,
        ):
            continue
        if not _matches_search_prefix(entry, search_prefix):
            continue
        items.append(entry)
    return items