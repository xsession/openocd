from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


SCRIPT_CALL_PATTERN = re.compile(
    r'runScript(?P<suffix>Basic|WithUpload|WithDownload)?\([^,]+,\s*'
    r'(?P<arg>"[^"]+"|(?:this\.)?[A-Za-z_][\w$]*(?:\(\))?)'
)
STRING_ASSIGNMENT_PATTERN = re.compile(
    r'\b(?:String\s+)?(?P<name>[A-Za-z_][\w$]*)\s*=\s*"(?P<value>[^"]+)"\s*;'
)
STRING_REFERENCE_ASSIGNMENT_PATTERN = re.compile(
    r'\b(?:String\s+)?(?P<name>[A-Za-z_][\w$]*)\s*=\s*(?P<value>(?:this\.)?[A-Za-z_][\w$]*(?:\(\))?)\s*;'
)
BYTE_ARRAY_LITERAL_ASSIGNMENT_PATTERN = re.compile(
    r'\b(?:byte\[\]\s+)?(?P<name>[A-Za-z_][\w$]*)\s*=\s*(?:new\s+byte\[\]\s*)?\{(?P<body>[^}]*)\}\s*;'
)
BYTE_ARRAY_LITERAL_START_PATTERN = re.compile(
    r'\b(?:byte\[\]\s+)?(?P<name>[A-Za-z_][\w$]*)\s*=\s*(?:new\s+byte\[\]\s*)?\{'
)
BYTE_ARRAY_REFERENCE_ASSIGNMENT_PATTERN = re.compile(
    r'\b(?:byte\[\]\s+)?(?P<name>[A-Za-z_][\w$]*)\s*=\s*(?P<value>(?:this\.)?[A-Za-z_][\w$]*)\s*;'
)
FIELD_BYTE_ARRAY_PATTERN = re.compile(
    r'^(?:\s)*(?:private|protected|public)\s+(?:(?:static|final)\s+)*byte\[\]\s+'
    r'(?P<name>[A-Za-z_][\w$]*)\s*=\s*(?:new\s+byte\[\]\s*)?\{(?P<body>[^}]*)\}\s*;\s*$'
)
FIELD_STRING_PATTERN = re.compile(
    r'^(?:\s)*(?:private|protected|public)\s+(?:(?:static|final)\s+)*String\s+'
    r'(?P<name>[A-Za-z_][\w$]*)\s*=\s*"(?P<value>[^"]+)"\s*;\s*$'
)
RETURN_STRING_PATTERN = re.compile(
    r'\breturn\s+(?P<expr>"[^"]+"|(?:this\.)?[A-Za-z_][\w$]*(?:\(\))?)\s*;'
)
METHOD_DECLARATION_PATTERN = re.compile(
    r'^\s*(public|protected|private)\s+'
    r'(?:(?:static|final|synchronized|native|abstract)\s+)*'
    r'(?:(?:[\w$<>\[\],.?]+)\s+)?'
    r'(?P<name>[A-Za-z_][\w$]*)\s*\([^;]*\)\s*'
    r'(?:throws\s+[^{]+)?\{$'
)
CLASS_DECLARATION_PATTERN = re.compile(
    r'public\s+(?:abstract\s+)?class\s+(?P<name>[A-Za-z_][\w$]*)'
    r'(?:\s+extends\s+(?P<extends>[A-Za-z_][\w$]*))?'
    r'(?:\s+implements\s+[^{]+)?'
)
CASE_PATTERN = re.compile(r'case\s+(?P<family>[A-Za-z0-9_]+)\s*:(?P<body>.*?)break;', re.S)
NEW_CLASS_PATTERN = re.compile(r'new\s+(?P<class_name>[A-Za-z_][\w$]*)\(this\)')

JAVA_BYTE_CONSTANTS = {
    "Byte.MIN_VALUE": -128,
    "Byte.MAX_VALUE": 127,
}

RAW_COMMAND_REFERENCE_TAGS = {
    "GET_RUNTIME_DATA_COMMAND": ("runtime", "query"),
    "holdInResetScript": ("reset", "assert"),
    "releaseFromResetScript": ("reset", "release"),
    "initPowerScript": ("power", "init"),
    "shutDownPowerSystem": ("power", "shutdown"),
    "scriptLiveconnect": ("target", "live-connect"),
    "powerTargetFromToolScript": ("power", "drive-target"),
    "powerGetSystemStatusScript": ("power", "status"),
    "setSelMaintainActivePower": ("power", "maintain-active"),
    "setLedBrightness": ("tool-config", "led"),
    "setSpeed": ("tool-config", "speed"),
    "setJTAGSpeed": ("tool-config", "jtag-speed"),
    "traceControlScriptNew": ("trace", "control"),
}

RAW_COMMAND_TAXONOMY = {
    "GET_RUNTIME_DATA_COMMAND": {"group": "runtime", "action": "query", "capabilities": ("runtime-status",)},
    "holdInResetScript": {"group": "reset", "action": "assert", "capabilities": ("target-reset-control",)},
    "releaseFromResetScript": {"group": "reset", "action": "release", "capabilities": ("target-reset-control",)},
    "initPowerScript": {"group": "power", "action": "init", "capabilities": ("target-power",)},
    "shutDownPowerSystem": {"group": "power", "action": "shutdown", "capabilities": ("target-power",)},
    "powerTargetFromToolScript": {"group": "power", "action": "drive-target", "capabilities": ("target-power",)},
    "powerGetSystemStatusScript": {"group": "power", "action": "status", "capabilities": ("target-power-status",)},
    "setSelMaintainActivePower": {"group": "power", "action": "maintain-active", "capabilities": ("target-power",)},
    "scriptLiveconnect": {"group": "target", "action": "live-connect", "capabilities": ("target-attach",)},
    "setLedBrightness": {"group": "tool-config", "action": "led", "capabilities": ("tool-led-control",)},
    "setSpeed": {"group": "tool-config", "action": "speed", "capabilities": ("tool-speed-control",)},
    "setJTAGSpeed": {"group": "tool-config", "action": "jtag-speed", "capabilities": ("tool-speed-control",)},
    "traceControlScriptNew": {"group": "trace", "action": "control", "capabilities": ("trace-control",)},
}

RAW_COMMAND_OPCODE_TAXONOMY = {
    0x1E: {"group": "runtime", "action": "query", "capabilities": ("runtime-status",)},
    0x39: {"group": "target", "action": "live-connect", "capabilities": ("target-attach",)},
    0x3B: {"group": "tool-config", "action": "speed", "capabilities": ("tool-speed-control",)},
    0x42: {"group": "reset", "action": "release", "capabilities": ("target-reset-control",)},
    0xB1: {"group": "reset", "action": "assert", "capabilities": ("target-reset-control",)},
    0xD4: {"group": "tool-config", "action": "jtag-speed", "capabilities": ("tool-speed-control",)},
    0xEC: {"group": "tool-config", "action": "speed", "capabilities": ("tool-speed-control",)},
    0xEF: {"group": "tool-config", "action": "payload", "capabilities": ("tool-script-payload",)},
}

RAW_COMMAND_SIGNATURE_TAXONOMY = {
    (0x40,): {
        "name": "power-init-sequence",
        "group": "power",
        "action": "init-sequence",
        "capabilities": ("target-power", "target-vpp-control"),
        "tags": ("power-init", "payload",),
    },
    (0x00, 0x00): {
        "name": "power-maintain-active-disable",
        "group": "power",
        "action": "maintain-active-disable",
        "capabilities": ("target-power", "target-power-hold"),
        "tags": ("disable", "power-hold",),
    },
    (0x00, 0x01): {
        "name": "power-maintain-active-enable",
        "group": "power",
        "action": "maintain-active-enable",
        "capabilities": ("target-power", "target-power-hold"),
        "tags": ("enable", "power-hold",),
    },
    (0x1E, 0x80): {
        "name": "runtime-data-query",
        "group": "runtime",
        "action": "query",
        "capabilities": ("runtime-status",),
        "tags": ("signature-runtime-query",),
    },
    (0x39, 0x00): {
        "name": "live-connect-disable",
        "group": "target",
        "action": "live-connect-disable",
        "capabilities": ("target-attach",),
        "tags": ("disable",),
    },
    (0x39, 0x01): {
        "name": "live-connect-enable",
        "group": "target",
        "action": "live-connect-enable",
        "capabilities": ("target-attach",),
        "tags": ("enable",),
    },
    (0x42,): {
        "name": "vpp-operational-value",
        "group": "power",
        "action": "vpp-operational-value",
        "capabilities": ("target-power", "target-vpp-control"),
        "tags": ("vpp",),
    },
    (0x42, 0xB0): {
        "name": "reset-release",
        "group": "reset",
        "action": "release",
        "capabilities": ("target-reset-control",),
        "tags": ("release-sequence",),
    },
    (0x44,): {
        "name": "power-shutdown",
        "group": "power",
        "action": "shutdown",
        "capabilities": ("target-power",),
        "tags": ("power-down",),
    },
    (0x46, 0x00): {
        "name": "power-target-from-tool-disable",
        "group": "power",
        "action": "drive-target-disable",
        "capabilities": ("target-power",),
        "tags": ("disable", "drive-target",),
    },
    (0x46, 0x01): {
        "name": "power-target-from-tool-enable",
        "group": "power",
        "action": "drive-target-enable",
        "capabilities": ("target-power",),
        "tags": ("enable", "drive-target",),
    },
    (0x47,): {
        "name": "power-system-status",
        "group": "power",
        "action": "status",
        "capabilities": ("target-power-status",),
        "tags": ("status-query",),
    },
    (0xB1,): {
        "name": "reset-assert",
        "group": "reset",
        "action": "assert",
        "capabilities": ("target-reset-control",),
        "tags": ("assert-sequence",),
    },
    (0xB1, 0x94, 0x01, 0x00, 0x42, 0xB0): {
        "name": "reset-cycle-release",
        "group": "reset",
        "action": "cycle-release",
        "capabilities": ("target-reset-control", "target-reset-pulse"),
        "tags": ("assert-release", "pulse",),
    },
    (0xCF,): {
        "name": "tool-led-brightness",
        "group": "tool-config",
        "action": "led-brightness",
        "capabilities": ("tool-led-control",),
        "tags": ("payload", "brightness",),
    },
    (0xEC,): {
        "name": "tool-speed-config-ec",
        "group": "tool-config",
        "action": "speed",
        "capabilities": ("tool-speed-control",),
        "tags": ("speed-config",),
    },
    (0xEF,): {
        "name": "tool-script-payload",
        "group": "tool-config",
        "action": "payload",
        "capabilities": ("tool-script-payload",),
        "tags": ("payload",),
    },
}


@dataclass(frozen=True)
class ScriptInvocation:
    script: str
    call_kind: str
    method_name: str
    line_number: int
    source_path: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "script": self.script,
            "callKind": self.call_kind,
            "methodName": self.method_name,
            "lineNumber": self.line_number,
            "sourcePath": self.source_path,
        }


@dataclass(frozen=True)
class RawCommandInvocation:
    reference: str
    call_kind: str
    method_name: str
    line_number: int
    source_path: str
    byte_tokens: Tuple[str, ...] = ()
    byte_values: Tuple[int, ...] = ()
    opcode_byte: Optional[int] = None
    signature_name: Optional[str] = None
    semantic_tags: Tuple[str, ...] = ()
    taxonomy_group: Optional[str] = None
    taxonomy_action: Optional[str] = None
    capability_tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "reference": self.reference,
            "callKind": self.call_kind,
            "methodName": self.method_name,
            "lineNumber": self.line_number,
            "sourcePath": self.source_path,
            "byteTokens": list(self.byte_tokens),
            "byteValues": list(self.byte_values),
            "opcodeByte": self.opcode_byte,
            "signatureName": self.signature_name,
            "semanticTags": list(self.semantic_tags),
            "taxonomyGroup": self.taxonomy_group,
            "taxonomyAction": self.taxonomy_action,
            "capabilityTags": list(self.capability_tags),
        }


@dataclass(frozen=True)
class JavaMethodKnowledge:
    name: str
    signature: str
    line_number: int
    script_invocations: Tuple[ScriptInvocation, ...]
    raw_command_invocations: Tuple[RawCommandInvocation, ...] = ()

    def script_names(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for invocation in self.script_invocations:
            if invocation.script not in seen:
                seen.add(invocation.script)
                ordered.append(invocation.script)
        return tuple(ordered)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "signature": self.signature,
            "lineNumber": self.line_number,
            "scripts": [invocation.to_dict() for invocation in self.script_invocations],
            "rawCommands": [invocation.to_dict() for invocation in self.raw_command_invocations],
        }


@dataclass(frozen=True)
class JavaClassKnowledge:
    name: str
    role: str
    source_path: str
    extends_class: Optional[str]
    methods: Tuple[JavaMethodKnowledge, ...]
    selector_method_values: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()

    def method_names(self) -> Tuple[str, ...]:
        return tuple(method.name for method in self.methods)

    def method(self, name: str) -> Optional[JavaMethodKnowledge]:
        for method in self.methods:
            if method.name == name:
                return method
        return None

    def direct_script_names(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for script_name in method.script_names():
                if script_name not in seen:
                    seen.add(script_name)
                    ordered.append(script_name)
        for method_name, script_values in self.selector_method_values:
            if "script" not in method_name.lower():
                continue
            for script_name in script_values:
                if script_name not in seen:
                    seen.add(script_name)
                    ordered.append(script_name)
        return tuple(ordered)

    def direct_raw_command_refs(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for invocation in method.raw_command_invocations:
                if invocation.reference not in seen:
                    seen.add(invocation.reference)
                    ordered.append(invocation.reference)
        return tuple(ordered)

    def raw_command_semantic_tags(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for invocation in method.raw_command_invocations:
                for tag in invocation.semantic_tags:
                    if tag not in seen:
                        seen.add(tag)
                        ordered.append(tag)
        return tuple(ordered)

    def raw_command_capability_tags(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for invocation in method.raw_command_invocations:
                for tag in invocation.capability_tags:
                    if tag not in seen:
                        seen.add(tag)
                        ordered.append(tag)
        return tuple(ordered)

    def raw_command_signature_names(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for invocation in method.raw_command_invocations:
                if invocation.signature_name and invocation.signature_name not in seen:
                    seen.add(invocation.signature_name)
                    ordered.append(invocation.signature_name)
        return tuple(ordered)

    def raw_command_taxonomy_groups(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for method in self.methods:
            for invocation in method.raw_command_invocations:
                if invocation.taxonomy_group and invocation.taxonomy_group not in seen:
                    seen.add(invocation.taxonomy_group)
                    ordered.append(invocation.taxonomy_group)
        return tuple(ordered)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "role": self.role,
            "sourcePath": self.source_path,
            "extendsClass": self.extends_class,
            "methods": [method.to_dict() for method in self.methods],
            "selectorMethods": [
                {"name": method_name, "values": list(script_values)}
                for method_name, script_values in self.selector_method_values
            ],
        }


@dataclass(frozen=True)
class JavaFamilyKnowledge:
    family: str
    programmer_class: str
    debugger_class: str
    programmer_lineage: Tuple[str, ...]
    debugger_lineage: Tuple[str, ...]
    programmer_scripts: Tuple[str, ...]
    debugger_scripts: Tuple[str, ...]
    programmer_raw_commands: Tuple[str, ...]
    debugger_raw_commands: Tuple[str, ...]
    programmer_raw_command_tags: Tuple[str, ...]
    debugger_raw_command_tags: Tuple[str, ...]
    programmer_raw_command_groups: Tuple[str, ...]
    debugger_raw_command_groups: Tuple[str, ...]
    programmer_raw_command_capabilities: Tuple[str, ...]
    debugger_raw_command_capabilities: Tuple[str, ...]
    programmer_raw_command_signatures: Tuple[str, ...]
    debugger_raw_command_signatures: Tuple[str, ...]

    def all_script_names(self) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen = set()
        for script_name in self.programmer_scripts + self.debugger_scripts:
            if script_name not in seen:
                seen.add(script_name)
                ordered.append(script_name)
        return tuple(ordered)

    def to_dict(self) -> Dict[str, object]:
        return {
            "family": self.family,
            "programmerClass": self.programmer_class,
            "debuggerClass": self.debugger_class,
            "programmerLineage": list(self.programmer_lineage),
            "debuggerLineage": list(self.debugger_lineage),
            "programmerScripts": list(self.programmer_scripts),
            "debuggerScripts": list(self.debugger_scripts),
            "programmerRawCommands": list(self.programmer_raw_commands),
            "debuggerRawCommands": list(self.debugger_raw_commands),
            "programmerRawCommandTags": list(self.programmer_raw_command_tags),
            "debuggerRawCommandTags": list(self.debugger_raw_command_tags),
            "programmerRawCommandGroups": list(self.programmer_raw_command_groups),
            "debuggerRawCommandGroups": list(self.debugger_raw_command_groups),
            "programmerRawCommandCapabilities": list(self.programmer_raw_command_capabilities),
            "debuggerRawCommandCapabilities": list(self.debugger_raw_command_capabilities),
            "programmerRawCommandSignatures": list(self.programmer_raw_command_signatures),
            "debuggerRawCommandSignatures": list(self.debugger_raw_command_signatures),
            "allScripts": list(self.all_script_names()),
        }


@dataclass(frozen=True)
class JavaRi4KnowledgeBase:
    source_root: str
    main_controller_path: str
    classes: Tuple[JavaClassKnowledge, ...]
    families: Tuple[JavaFamilyKnowledge, ...]

    def class_map(self) -> Dict[str, JavaClassKnowledge]:
        return {item.name: item for item in self.classes}

    def family_map(self) -> Dict[str, JavaFamilyKnowledge]:
        return {item.family.upper(): item for item in self.families}

    def get_class(self, name: str) -> Optional[JavaClassKnowledge]:
        return self.class_map().get(name)

    def get_family(self, family: str) -> Optional[JavaFamilyKnowledge]:
        return self.family_map().get(family.upper())

    def to_dict(self) -> Dict[str, object]:
        return {
            "sourceRoot": self.source_root,
            "mainControllerPath": self.main_controller_path,
            "classes": [item.to_dict() for item in self.classes],
            "families": [item.to_dict() for item in self.families],
        }


def default_java_source_root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "_mplab_sys"
        / "mplablibs"
        / "src"
        / "com"
        / "microchip"
        / "mplab"
        / "libs"
        / "RI4ToolsController"
    )


@lru_cache(maxsize=None)
def load_java_ri4_knowledge(source_root: Optional[Path] = None) -> JavaRi4KnowledgeBase:
    root = source_root or default_java_source_root()
    main_controller_path = root / "MainController.java"
    programmer_root = root / "programmer"
    dispatch = _parse_family_dispatch(main_controller_path.read_text(encoding="utf-8", errors="ignore"))
    parsed_classes = [
        item
        for item in (_parse_java_class(path, root) for path in programmer_root.glob("*.java"))
        if item is not None
    ]
    classes = tuple(sorted(parsed_classes, key=lambda item: item.name))
    class_map = {item.name: item for item in classes}
    families = tuple(
        sorted(
            (
                JavaFamilyKnowledge(
                    family=family,
                    programmer_class=programmer_class,
                    debugger_class=debugger_class,
                    programmer_lineage=_class_lineage(programmer_class, class_map),
                    debugger_lineage=_class_lineage(debugger_class, class_map),
                    programmer_scripts=_aggregate_script_names(programmer_class, class_map),
                    debugger_scripts=_aggregate_script_names(debugger_class, class_map),
                    programmer_raw_commands=_aggregate_raw_command_refs(programmer_class, class_map),
                    debugger_raw_commands=_aggregate_raw_command_refs(debugger_class, class_map),
                    programmer_raw_command_tags=_aggregate_raw_command_tags(programmer_class, class_map),
                    debugger_raw_command_tags=_aggregate_raw_command_tags(debugger_class, class_map),
                    programmer_raw_command_groups=_aggregate_raw_command_groups(programmer_class, class_map),
                    debugger_raw_command_groups=_aggregate_raw_command_groups(debugger_class, class_map),
                    programmer_raw_command_capabilities=_aggregate_raw_command_capabilities(programmer_class, class_map),
                    debugger_raw_command_capabilities=_aggregate_raw_command_capabilities(debugger_class, class_map),
                    programmer_raw_command_signatures=_aggregate_raw_command_signatures(programmer_class, class_map),
                    debugger_raw_command_signatures=_aggregate_raw_command_signatures(debugger_class, class_map),
                )
                for family, programmer_class, debugger_class in dispatch
            ),
            key=lambda item: item.family,
        )
    )
    return JavaRi4KnowledgeBase(
        source_root=str(root),
        main_controller_path=str(main_controller_path),
        classes=classes,
        families=families,
    )


def dump_java_ri4_knowledge(source_root: Optional[Path] = None) -> str:
    return json.dumps(load_java_ri4_knowledge(source_root).to_dict(), indent=2, sort_keys=True)


def _parse_family_dispatch(source: str) -> List[Tuple[str, str, str]]:
    dispatch: List[Tuple[str, str, str]] = []
    for match in CASE_PATTERN.finditer(source):
        family = match.group("family")
        class_names = NEW_CLASS_PATTERN.findall(match.group("body"))
        if len(class_names) >= 2:
            dispatch.append((family, class_names[0], class_names[1]))
    return dispatch


def _parse_java_class(path: Path, root: Path) -> Optional[JavaClassKnowledge]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    declaration = CLASS_DECLARATION_PATTERN.search(text)
    if not declaration:
        return None
    class_name = declaration.group("name")
    extends_class = declaration.group("extends")
    role = _class_role(class_name)
    source_path = _relative_source_path(path, root)
    field_strings = _extract_class_string_values(text)
    field_byte_arrays = _extract_class_byte_array_values(text)
    method_strings = _extract_method_string_values(text, field_strings)
    methods = tuple(_extract_methods(text, source_path, field_strings, method_strings, field_byte_arrays))
    return JavaClassKnowledge(
        name=class_name,
        role=role,
        source_path=source_path,
        extends_class=extends_class,
        methods=methods,
        selector_method_values=tuple(sorted(method_strings.items())),
    )


def _extract_methods(
    source: str,
    source_path: str,
    field_strings: Dict[str, Tuple[str, ...]],
    method_strings: Dict[str, Tuple[str, ...]],
    field_byte_arrays: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]],
) -> Iterable[JavaMethodKnowledge]:
    lines = source.splitlines()
    active_name: Optional[str] = None
    active_signature: Optional[str] = None
    active_start: Optional[int] = None
    active_lines: List[str] = []
    brace_depth = 0
    for index, line in enumerate(lines, start=1):
        if active_name is None:
            match = METHOD_DECLARATION_PATTERN.match(line.strip())
            if not match:
                continue
            active_name = match.group("name")
            active_signature = line.strip()
            active_start = index
            active_lines = [line]
            brace_depth = line.count("{") - line.count("}")
            continue
        active_lines.append(line)
        brace_depth += line.count("{") - line.count("}")
        if brace_depth > 0:
            continue
        invocations = _extract_script_invocations(
            method_name=active_name,
            method_lines=active_lines,
            start_line=active_start or index,
            source_path=source_path,
            field_strings=field_strings,
            method_strings=method_strings,
            field_byte_arrays=field_byte_arrays,
        )
        if invocations[0] or invocations[1]:
            yield JavaMethodKnowledge(
                name=active_name,
                signature=active_signature or active_name,
                line_number=active_start or index,
                script_invocations=tuple(invocations[0]),
                raw_command_invocations=tuple(invocations[1]),
            )
        active_name = None
        active_signature = None
        active_start = None
        active_lines = []
        brace_depth = 0


def _extract_script_invocations(
    method_name: str,
    method_lines: Sequence[str],
    start_line: int,
    source_path: str,
    field_strings: Dict[str, Tuple[str, ...]],
    method_strings: Dict[str, Tuple[str, ...]],
    field_byte_arrays: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]],
) -> Tuple[List[ScriptInvocation], List[RawCommandInvocation]]:
    invocations: List[ScriptInvocation] = []
    raw_invocations: List[RawCommandInvocation] = []
    string_values: Dict[str, List[str]] = {}
    local_byte_arrays: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = {}
    pending_byte_statement: List[str] = []
    for offset, line in enumerate(method_lines):
        stripped_line = line.strip()
        if pending_byte_statement:
            pending_byte_statement.append(stripped_line)
            if "}" in stripped_line and ";" in stripped_line:
                literal_assignment = _parse_byte_array_literal_assignment(" ".join(pending_byte_statement))
                if literal_assignment is not None:
                    _merge_local_byte_array_value(
                        local_byte_arrays,
                        literal_assignment[0],
                        ((literal_assignment[0], literal_assignment[1]),),
                    )
                pending_byte_statement = []
            continue
        literal_assignment = _parse_byte_array_literal_assignment(stripped_line)
        if literal_assignment is not None:
            _merge_local_byte_array_value(
                local_byte_arrays,
                literal_assignment[0],
                ((literal_assignment[0], literal_assignment[1]),),
            )
        elif _is_byte_array_literal_start(stripped_line):
            pending_byte_statement = [stripped_line]
            continue
        for assignment in STRING_ASSIGNMENT_PATTERN.finditer(line):
            variable_name = assignment.group("name")
            literal_value = assignment.group("value")
            values = string_values.setdefault(variable_name, [])
            if literal_value not in values:
                values.append(literal_value)
        for assignment in STRING_REFERENCE_ASSIGNMENT_PATTERN.finditer(line):
            variable_name = assignment.group("name")
            resolved_values = _resolve_string_expression(
                assignment.group("value"),
                local_strings=string_values,
                field_strings=field_strings,
                method_strings=method_strings,
            )
            if not resolved_values:
                continue
            values = string_values.setdefault(variable_name, [])
            for resolved_value in resolved_values:
                if resolved_value not in values:
                    values.append(resolved_value)
        for assignment in BYTE_ARRAY_REFERENCE_ASSIGNMENT_PATTERN.finditer(line):
            resolved_commands = _resolve_raw_command_expression(
                assignment.group("value"),
                local_byte_arrays=local_byte_arrays,
                field_byte_arrays=field_byte_arrays,
            )
            if resolved_commands:
                _merge_local_byte_array_value(local_byte_arrays, assignment.group("name"), resolved_commands)
        for match in SCRIPT_CALL_PATTERN.finditer(line):
            suffix = match.group("suffix") or ""
            call_kind = {
                "": "execute",
                "Basic": "basic",
                "WithUpload": "upload",
                "WithDownload": "download",
            }[suffix]
            script_names = _resolve_string_expression(
                match.group("arg"),
                local_strings=string_values,
                field_strings=field_strings,
                method_strings=method_strings,
            )
            for script_name in script_names:
                invocations.append(
                    ScriptInvocation(
                        script=script_name,
                        call_kind=call_kind,
                        method_name=method_name,
                        line_number=start_line + offset,
                        source_path=source_path,
                    )
                )
            if script_names:
                continue
            for reference, byte_tokens in _resolve_raw_command_expression(
                match.group("arg"),
                local_byte_arrays=local_byte_arrays,
                field_byte_arrays=field_byte_arrays,
            ):
                byte_values = _decode_byte_tokens(byte_tokens)
                raw_invocations.append(
                    RawCommandInvocation(
                        reference=reference,
                        call_kind=call_kind,
                        method_name=method_name,
                        line_number=start_line + offset,
                        source_path=source_path,
                        byte_tokens=byte_tokens,
                        byte_values=byte_values,
                        opcode_byte=_opcode_byte(byte_tokens),
                        signature_name=_signature_name(byte_values),
                        semantic_tags=_semantic_tags(reference, byte_values),
                        taxonomy_group=_taxonomy_group(reference, byte_values),
                        taxonomy_action=_taxonomy_action(reference, byte_values),
                        capability_tags=_capability_tags(reference, byte_values),
                    )
                )
    return invocations, raw_invocations


def _extract_class_string_values(source: str) -> Dict[str, Tuple[str, ...]]:
    values: Dict[str, Tuple[str, ...]] = {}
    for line in source.splitlines():
        match = FIELD_STRING_PATTERN.match(line)
        if match:
            values[match.group("name")] = (match.group("value"),)
    return values


def _extract_class_byte_array_values(source: str) -> Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]]:
    values: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {}
    for line in source.splitlines():
        match = FIELD_BYTE_ARRAY_PATTERN.match(line)
        if match:
            values[match.group("name")] = ((match.group("name"), _parse_byte_tokens(match.group("body"))),)
    return values


def _extract_method_string_values(
    source: str,
    field_strings: Dict[str, Tuple[str, ...]],
) -> Dict[str, Tuple[str, ...]]:
    values: Dict[str, Tuple[str, ...]] = {}
    lines = source.splitlines()
    active_name: Optional[str] = None
    active_lines: List[str] = []
    brace_depth = 0
    for line in lines:
        if active_name is None:
            match = METHOD_DECLARATION_PATTERN.match(line.strip())
            if not match:
                continue
            active_name = match.group("name")
            active_lines = [line]
            brace_depth = line.count("{") - line.count("}")
            continue
        active_lines.append(line)
        brace_depth += line.count("{") - line.count("}")
        if brace_depth > 0:
            continue
        method_values = _extract_returned_string_values(active_lines, field_strings)
        if method_values:
            values[active_name] = tuple(method_values)
        active_name = None
        active_lines = []
        brace_depth = 0
    return values


def _extract_returned_string_values(
    method_lines: Sequence[str],
    field_strings: Dict[str, Tuple[str, ...]],
) -> List[str]:
    values: List[str] = []
    local_strings: Dict[str, List[str]] = {}
    for line in method_lines:
        for assignment in STRING_ASSIGNMENT_PATTERN.finditer(line):
            local_values = local_strings.setdefault(assignment.group("name"), [])
            literal_value = assignment.group("value")
            if literal_value not in local_values:
                local_values.append(literal_value)
        for assignment in STRING_REFERENCE_ASSIGNMENT_PATTERN.finditer(line):
            local_values = local_strings.setdefault(assignment.group("name"), [])
            for resolved_value in _resolve_string_expression(
                assignment.group("value"),
                local_strings=local_strings,
                field_strings=field_strings,
                method_strings={},
            ):
                if resolved_value not in local_values:
                    local_values.append(resolved_value)
        for match in RETURN_STRING_PATTERN.finditer(line):
            for resolved_value in _resolve_string_expression(
                match.group("expr"),
                local_strings=local_strings,
                field_strings=field_strings,
                method_strings={},
            ):
                if resolved_value not in values:
                    values.append(resolved_value)
    return values


def _resolve_string_expression(
    expression: Optional[str],
    *,
    local_strings: Dict[str, List[str]],
    field_strings: Dict[str, Tuple[str, ...]],
    method_strings: Dict[str, Tuple[str, ...]],
) -> Tuple[str, ...]:
    if not expression:
        return ()
    expr = expression.strip()
    if expr.startswith('"') and expr.endswith('"'):
        return (expr[1:-1],)
    if expr.startswith("this."):
        expr = expr[5:]
    if expr.endswith("()"):
        return method_strings.get(expr[:-2], ())
    if expr in local_strings:
        return tuple(local_strings[expr])
    if expr in field_strings:
        return field_strings[expr]
    return ()


def _resolve_raw_command_expression(
    expression: Optional[str],
    *,
    local_byte_arrays: Dict[str, List[Tuple[str, Tuple[str, ...]]]],
    field_byte_arrays: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]],
) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    if not expression:
        return ()
    expr = expression.strip()
    if expr.startswith('"') and expr.endswith('"'):
        return ()
    if expr.startswith("this."):
        expr = expr[5:]
    if expr in local_byte_arrays:
        return tuple(local_byte_arrays[expr])
    if expr in field_byte_arrays:
        return field_byte_arrays[expr]
    return ((expr, ()),)


def _parse_byte_tokens(body: str) -> Tuple[str, ...]:
    tokens = [token.strip() for token in body.split(",") if token.strip()]
    return tuple(tokens)


def _parse_byte_array_literal_assignment(statement: str) -> Optional[Tuple[str, Tuple[str, ...]]]:
    match = BYTE_ARRAY_LITERAL_ASSIGNMENT_PATTERN.search(statement)
    if not match:
        return None
    return match.group("name"), _parse_byte_tokens(match.group("body"))


def _is_byte_array_literal_start(statement: str) -> bool:
    return BYTE_ARRAY_LITERAL_START_PATTERN.search(statement) is not None


def _merge_local_byte_array_value(
    local_byte_arrays: Dict[str, List[Tuple[str, Tuple[str, ...]]]],
    name: str,
    commands: Tuple[Tuple[str, Tuple[str, ...]], ...],
) -> None:
    values = local_byte_arrays.setdefault(name, [])
    for command in commands:
      if command not in values:
        values.append(command)


def _decode_byte_tokens(tokens: Tuple[str, ...]) -> Tuple[int, ...]:
    values: List[int] = []
    for token in tokens:
        parsed = _parse_java_byte_token(token)
        if parsed is None:
            break
        values.append(parsed)
    return tuple(values)


def _opcode_byte(tokens: Tuple[str, ...]) -> Optional[int]:
    decoded = _decode_byte_tokens(tokens)
    if not decoded:
        return None
    return decoded[0] & 0xFF


def _parse_java_byte_token(token: str) -> Optional[int]:
    normalized = token.strip()
    if not normalized:
        return None
    if normalized in JAVA_BYTE_CONSTANTS:
        return JAVA_BYTE_CONSTANTS[normalized]
    if normalized.startswith("(byte)"):
        normalized = normalized[6:].strip()
    try:
        return int(normalized, 0)
    except ValueError:
        return None


def _semantic_tags(reference: str, byte_values: Tuple[int, ...]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for tag in RAW_COMMAND_REFERENCE_TAGS.get(reference, ()): 
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    if byte_values:
        first = byte_values[0] & 0xFF
        opcode_tag = f"opcode:{first:02X}"
        if opcode_tag not in seen:
            seen.add(opcode_tag)
            ordered.append(opcode_tag)
    signature_taxonomy = _signature_taxonomy(byte_values)
    if signature_taxonomy is not None:
        signature_tag = f"signature:{signature_taxonomy['name']}"
        if signature_tag not in seen:
            seen.add(signature_tag)
            ordered.append(signature_tag)
        for extra_tag in signature_taxonomy.get("tags", ()): 
            if str(extra_tag) not in seen:
                seen.add(str(extra_tag))
                ordered.append(str(extra_tag))
        for extra_tag in (str(signature_taxonomy["group"]), str(signature_taxonomy["action"])):
            if extra_tag not in seen:
                seen.add(extra_tag)
                ordered.append(extra_tag)
        return tuple(ordered)
    if byte_values:
        opcode_taxonomy = RAW_COMMAND_OPCODE_TAXONOMY.get(byte_values[0] & 0xFF)
        if opcode_taxonomy is not None:
            for extra_tag in (str(opcode_taxonomy["group"]), str(opcode_taxonomy["action"])):
                if extra_tag not in seen:
                    seen.add(extra_tag)
                    ordered.append(extra_tag)
    return tuple(ordered)


def _taxonomy_group(reference: str, byte_values: Tuple[int, ...]) -> Optional[str]:
    taxonomy = RAW_COMMAND_TAXONOMY.get(reference)
    signature_taxonomy = _signature_taxonomy(byte_values)
    if signature_taxonomy is not None:
        return str(signature_taxonomy["group"])
    if taxonomy is not None:
        return str(taxonomy["group"])
    fallback = _opcode_taxonomy_from_reference(reference, byte_values)
    if fallback is None:
        return None
    return str(fallback["group"])


def _taxonomy_action(reference: str, byte_values: Tuple[int, ...]) -> Optional[str]:
    taxonomy = RAW_COMMAND_TAXONOMY.get(reference)
    signature_taxonomy = _signature_taxonomy(byte_values)
    if signature_taxonomy is not None:
        return str(signature_taxonomy["action"])
    if taxonomy is not None:
        return str(taxonomy["action"])
    fallback = _opcode_taxonomy_from_reference(reference, byte_values)
    if fallback is None:
        return None
    return str(fallback["action"])


def _capability_tags(reference: str, byte_values: Tuple[int, ...]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for taxonomy in (
        RAW_COMMAND_TAXONOMY.get(reference),
        _signature_taxonomy(byte_values),
        _opcode_taxonomy_from_reference(reference, byte_values),
    ):
        if taxonomy is None:
            continue
        for capability in taxonomy.get("capabilities", ()):
            text = str(capability)
            if text in seen:
                continue
            seen.add(text)
            ordered.append(text)
    return tuple(ordered)


def _opcode_taxonomy_from_reference(reference: str, byte_values: Tuple[int, ...]) -> Optional[Dict[str, object]]:
    if byte_values:
        opcode_taxonomy = RAW_COMMAND_OPCODE_TAXONOMY.get(byte_values[0] & 0xFF)
        if opcode_taxonomy is not None:
            return opcode_taxonomy
    # Fallback taxonomy is keyed by opcode-family references once the invocation has
    # been normalized into the symbolic raw-command reference layer.
    known_reference_opcodes = {
        "GET_RUNTIME_DATA_COMMAND": 0x1E,
        "holdInResetScript": 0xB1,
        "releaseFromResetScript": 0x42,
        "scriptLiveconnect": 0x39,
        "setSpeed": 0x3B,
        "setJTAGSpeed": 0xD4,
        "scriptContent": 0xEF,
    }
    opcode = known_reference_opcodes.get(reference)
    if opcode is None:
        return None
    return RAW_COMMAND_OPCODE_TAXONOMY.get(opcode)


def _signature_taxonomy(byte_values: Tuple[int, ...]) -> Optional[Dict[str, object]]:
    if not byte_values:
        return None
    normalized = tuple(value & 0xFF for value in byte_values)
    best_match: Optional[Dict[str, object]] = None
    best_length = -1
    for signature, taxonomy in RAW_COMMAND_SIGNATURE_TAXONOMY.items():
        if len(signature) > len(normalized):
            continue
        if normalized[: len(signature)] != signature:
            continue
        if len(signature) <= best_length:
            continue
        best_match = taxonomy
        best_length = len(signature)
    return best_match


def _signature_name(byte_values: Tuple[int, ...]) -> Optional[str]:
    taxonomy = _signature_taxonomy(byte_values)
    if taxonomy is None:
        return None
    return str(taxonomy["name"])


def _class_role(class_name: str) -> str:
    if class_name.startswith("Programmer"):
        return "programmer"
    if class_name.startswith("Debugger"):
        return "debugger"
    return "other"


def _class_lineage(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    lineage: List[str] = []
    current = class_name
    seen = set()
    while current and current not in seen:
        seen.add(current)
        lineage.append(current)
        item = class_map.get(current)
        if item is None:
            break
        current = item.extends_class or ""
    return tuple(lineage)


def _aggregate_script_names(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for script_name in item.direct_script_names():
            if script_name not in seen:
                seen.add(script_name)
                ordered.append(script_name)
    return tuple(ordered)


def _aggregate_raw_command_refs(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for reference in item.direct_raw_command_refs():
            if reference not in seen:
                seen.add(reference)
                ordered.append(reference)
    return tuple(ordered)


def _aggregate_raw_command_tags(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for tag in item.raw_command_semantic_tags():
            if tag not in seen:
                seen.add(tag)
                ordered.append(tag)
    return tuple(ordered)


def _aggregate_raw_command_groups(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for group in item.raw_command_taxonomy_groups():
            if group not in seen:
                seen.add(group)
                ordered.append(group)
    return tuple(ordered)


def _aggregate_raw_command_capabilities(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for capability in item.raw_command_capability_tags():
            if capability not in seen:
                seen.add(capability)
                ordered.append(capability)
    return tuple(ordered)


def _aggregate_raw_command_signatures(class_name: str, class_map: Dict[str, JavaClassKnowledge]) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen = set()
    for lineage_class in _class_lineage(class_name, class_map):
        item = class_map.get(lineage_class)
        if item is None:
            continue
        for signature_name in item.raw_command_signature_names():
            if signature_name not in seen:
                seen.add(signature_name)
                ordered.append(signature_name)
    return tuple(ordered)


def _relative_source_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Dump structured RI4 Java knowledge as JSON")
    parser.add_argument("--family", help="Filter output to a single device family")
    args = parser.parse_args(argv)
    knowledge = load_java_ri4_knowledge()
    if args.family:
        family = knowledge.get_family(args.family)
        if family is None:
            raise SystemExit(f"Unknown family: {args.family}")
        print(json.dumps(family.to_dict(), indent=2, sort_keys=True))
        return 0
    print(json.dumps(knowledge.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())