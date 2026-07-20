from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .errors import Ri4ProtocolError
from .script import Script


def _parse_unsigned_byte(text: str) -> int:
    s = text.strip()
    if s.lower().startswith("0x"):
        v = int(s[2:], 16)
    else:
        v = int(s, 10)
    return v & 0xFF


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _find_first_text(elem: ET.Element, wanted_local: str) -> Optional[str]:
    for sub in elem.iter():
        if _local_name(sub.tag) == wanted_local:
            return sub.text
    return None


def _find_first_elem(elem: ET.Element, wanted_local: str) -> Optional[ET.Element]:
    for sub in elem.iter():
        if _local_name(sub.tag) == wanted_local:
            return sub
    return None


def _parse_xml_path(path: str) -> ET.Element:
    if str(path).lower().endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            return ET.parse(handle).getroot()
    return ET.parse(path).getroot()


def _read_text_path(path: str) -> str:
    if str(path).lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return handle.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _parse_yaml_scalar(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        inner = value[1:-1]
        return inner.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    return value


def _yaml_line_indent(line: str) -> int:
    return (len(line) - len(line.lstrip(" "))) // 2


def _parse_yaml_node(lines: List[str], index: int, indent: int) -> Tuple[object, int]:
    if index >= len(lines):
        return {}, index
    stripped = lines[index].strip()
    if stripped.startswith("-"):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_dict(lines, index, indent)


def _parse_yaml_dict(lines: List[str], index: int, indent: int) -> Tuple[Dict[str, object], int]:
    data: Dict[str, object] = {}
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        current_indent = _yaml_line_indent(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise Ri4ProtocolError(f"Unexpected YAML indentation at line: {line}")
        stripped = line.strip()
        if stripped.startswith("-"):
            break
        key, _, value = stripped.partition(":")
        key = _parse_yaml_scalar(key)
        value = value.strip()
        if value == "{}":
            data[key] = {}
            index += 1
            continue
        if value:
            data[key] = _parse_yaml_scalar(value)
            index += 1
            continue
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or _yaml_line_indent(lines[index]) <= indent:
            data[key] = {}
            continue
        child, index = _parse_yaml_node(lines, index, indent + 1)
        data[key] = child
    return data, index


def _parse_yaml_list(lines: List[str], index: int, indent: int) -> Tuple[List[object], int]:
    items: List[object] = []
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        current_indent = _yaml_line_indent(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise Ri4ProtocolError(f"Unexpected YAML indentation at line: {line}")
        stripped = line.strip()
        if not stripped.startswith("-"):
            break
        rest = stripped[1:].strip()
        if rest == "{}":
            items.append({})
            index += 1
            continue
        if rest:
            items.append(_parse_yaml_scalar(rest))
            index += 1
            continue
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or _yaml_line_indent(lines[index]) <= indent:
            items.append({})
            continue
        child, index = _parse_yaml_node(lines, index, indent + 1)
        items.append(child)
    return items, index


def _normalize_children(node: object) -> Dict[str, object]:
    if not isinstance(node, dict):
        return {}
    children = node.get("children")
    return children if isinstance(children, dict) else {}


def _child_text(node: object, key: str) -> Optional[str]:
    child = _normalize_children(node).get(key)
    if isinstance(child, dict):
        text = child.get("text")
        return str(text) if text is not None else None
    return None


def _child_list(node: object, key: str) -> List[object]:
    child = _normalize_children(node).get(key)
    if isinstance(child, list):
        return child
    if child is None:
        return []
    return [child]


def _parse_yaml_device_file(processor: str, path: str) -> "DeviceFile":
    parsed, _ = _parse_yaml_node([line for line in _read_text_path(path).splitlines() if line.strip()], 0, 0)
    if not isinstance(parsed, dict):
        raise Ri4ProtocolError("Invalid exported YAML format")
    document = parsed.get("document")
    if not isinstance(document, dict) or not document:
        raise Ri4ProtocolError("Exported YAML is missing document root")
    root = next(iter(document.values()))
    version = _child_text(root, "version")
    commit = _child_text(root, "commit")

    target = processor.strip().lower()
    top_processors = [str(item.get("text", "")).strip().lower() for item in _child_list(root, "processor") if isinstance(item, dict)]
    collect_without_nested_processor = target in top_processors

    scripts: List[Script] = []
    for script_node in _child_list(root, "script"):
        if not isinstance(script_node, dict):
            continue
        script_processor = (_child_text(script_node, "processor") or "").strip().lower()
        if script_processor:
            if script_processor != target:
                continue
        elif not collect_without_nested_processor:
            continue

        fn = (_child_text(script_node, "function") or "").strip()
        if not fn:
            raise Ri4ProtocolError("script missing <function>")

        data_bytes: List[int] = []
        scrbytes = _normalize_children(script_node).get("scrbytes")
        for byte_node in _child_list(scrbytes, "byte"):
            if not isinstance(byte_node, dict):
                continue
            byte_text = byte_node.get("text")
            if byte_text is None:
                continue
            data_bytes.append(_parse_unsigned_byte(str(byte_text)))

        scripts.append(Script(method=fn, data=bytes(data_bytes)))

    return DeviceFile(processor=processor, scripts=scripts, version=version, commit=commit)


@dataclass
class DeviceFile:
    """Parsed scripts.xml-like content.

    Clean-room port of the Java SAX reader behavior:
    - Filters by <processor>
    - Builds Script(method=<function>, data=<scrbytes>)
    - Supports optional script suffix lookup
    """

    processor: str
    scripts: List[Script]
    version: Optional[str] = None
    commit: Optional[str] = None
    script_suffix: Optional[str] = None

    @classmethod
    def from_xml_text(cls, processor: str, xml_text: str) -> "DeviceFile":
        root = ET.fromstring(xml_text)
        return cls.from_xml_root(processor, root)

    @classmethod
    def from_xml_path(cls, processor: str, path: str) -> "DeviceFile":
        lower_path = str(path).lower()
        if lower_path.endswith(".yaml") or lower_path.endswith(".yaml.gz"):
            return _parse_yaml_device_file(processor, path)
        return cls.from_xml_root(processor, _parse_xml_path(path))

    @classmethod
    def from_xml_root(cls, processor: str, root: ET.Element) -> "DeviceFile":
        version = _find_first_text(root, "version")
        commit = _find_first_text(root, "commit")

        scripts: List[Script] = []

        # Java handler updates shouldCollect from the most recent <processor>.
        should_collect = False
        target = processor.strip().lower()

        for child in list(root):
            tag = _local_name(child.tag)
            if tag == "processor":
                should_collect = (child.text or "").strip().lower() == target
                continue

            if tag != "script":
                continue

            # MPLAB toolpacks commonly nest <processor> inside each <script> rather than
            # using the older top-level processor toggle layout.
            script_processor = (_find_first_text(child, "processor") or "").strip().lower()
            collect_script = should_collect or script_processor == target
            if not collect_script:
                continue

            fn = (_find_first_text(child, "function") or "").strip()
            if not fn:
                raise Ri4ProtocolError("script missing <function>")

            scrbytes = _find_first_elem(child, "scrbytes")
            data_bytes: List[int] = []
            if scrbytes is not None:
                for b in list(scrbytes):
                    if _local_name(b.tag) != "byte":
                        continue
                    if b.text is None:
                        continue
                    data_bytes.append(_parse_unsigned_byte(b.text))

            scripts.append(Script(method=fn, data=bytes(data_bytes)))

        return cls(processor=processor, scripts=scripts, version=version, commit=commit)

    def set_script_suffix(self, suf: str) -> None:
        self.script_suffix = suf

    # Java-compat naming
    def setScriptSuffix(self, suf: str) -> None:
        self.set_script_suffix(suf)

    def getScripts(self) -> List[Script]:
        return list(self.scripts)

    def get_script_basic(self, name: str) -> Optional[Script]:
        n = name.lower()
        suf = self.script_suffix
        for s in self.scripts:
            if s.method.lower() == n:
                return s
            if suf is not None and s.method.lower() == (name + suf).lower():
                return s
        return None

    # Java-compat naming
    def getScriptBasic(self, name: str) -> Optional[Script]:
        return self.get_script_basic(name)

    def get_script(self, name: str) -> Script:
        s = self.get_script_basic(name)
        if s is None:
            raise Ri4ProtocolError(f"Script '{name}' for processor '{self.processor}' not found")
        return s

    # Java-compat naming
    def getScript(self, name: str) -> Script:
        return self.get_script(name)


class DeviceFileSAXReader(DeviceFile):
    """Compatibility wrapper for the Java class name.

    The Java constructor takes (processor, InputStream). Here we accept a file-like
    object with .read() returning bytes/str, or a raw XML string/bytes.
    """

    def __init__(self, processor: str, is_):
        if hasattr(is_, "read"):
            raw = is_.read()
            try:
                is_.close()
            except Exception:
                pass
        else:
            raw = is_

        if isinstance(raw, bytes):
            xml_text = raw.decode("utf-8", errors="replace")
        else:
            xml_text = str(raw)

        df = DeviceFile.from_xml_text(processor, xml_text)
        super().__init__(
            processor=df.processor,
            scripts=df.scripts,
            version=df.version,
            commit=df.commit,
            script_suffix=df.script_suffix,
        )
