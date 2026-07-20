from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def attrs_ci(element: ET.Element) -> dict[str, str]:
    return {k.rsplit("}", 1)[-1].lower(): v for k, v in element.attrib.items()}


def parse_int(value: str | int | None, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip().replace("_", "")
    if not text:
        return default
    text = re.sub(r"[uUlL]+$", "", text)
    if text.lower().endswith("h") and re.fullmatch(r"[0-9a-fA-F]+h", text):
        return int(text[:-1], 16)
    try:
        return int(text, 0)
    except ValueError:
        match = re.search(r"0x[0-9a-fA-F]+|\d+", text)
        return int(match.group(0), 0) if match else default


def first_attr(element: ET.Element, *names: str) -> str | None:
    attrs = attrs_ci(element)
    for name in names:
        if name.lower() in attrs and attrs[name.lower()].strip():
            return attrs[name.lower()].strip()
    return None


def child_property(element: ET.Element, *names: str) -> str | None:
    wanted = {name.lower() for name in names}
    direct = first_attr(element, *names)
    if direct is not None:
        return direct
    for child in element:
        tag = local_name(child.tag)
        attrs = attrs_ci(child)
        if tag in wanted and child.text and child.text.strip():
            return child.text.strip()
        key = attrs.get("name", attrs.get("id", "")).lower()
        if key in wanted:
            return attrs.get("value") or (child.text.strip() if child.text else None)
    return None


def sanitize_identifier(text: str, fallback: str = "UNNAMED") -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", text.strip())
    value = re.sub(r"_+", "_", value).strip("_") or fallback
    if value[0].isdigit():
        value = "_" + value
    return value.upper()


def normalize_access(value: str | None, default: str = "read-write") -> str:
    if not value:
        return default
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "r": "read-only", "ro": "read-only", "read": "read-only",
        "readonly": "read-only", "read-only": "read-only",
        "w": "write-only", "wo": "write-only", "write": "write-only",
        "writeonly": "write-only", "write-only": "write-only",
        "rw": "read-write", "wr": "read-write", "readwrite": "read-write",
        "read-write": "read-write", "write-read": "read-write",
    }
    return aliases.get(key, default)


def indent_xml(root: ET.Element) -> None:
    ET.indent(root, space="  ")


def find_case_insensitive(base: Path, relative: str) -> Path | None:
    candidate = base / relative
    if candidate.exists():
        return candidate
    current = base
    for part in Path(relative).parts:
        if not current.is_dir():
            return None
        match = next((p for p in current.iterdir() if p.name.lower() == part.lower()), None)
        if match is None:
            return None
        current = match
    return current
