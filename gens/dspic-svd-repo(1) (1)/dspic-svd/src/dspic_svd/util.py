from __future__ import annotations

import re
from xml.etree.ElementTree import Element

_IDENTIFIER = re.compile(r"[^A-Za-z0-9_]")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def attrs_by_local(element: Element) -> dict[str, str]:
    return {local_name(k): v for k, v in element.attrib.items()}


def first_attr(element: Element, *names: str, default: str | None = None) -> str | None:
    attrs = attrs_by_local(element)
    for name in names:
        if name in attrs and attrs[name] != "":
            return attrs[name]
    return default


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    text = value.strip().replace("_", "")
    if not text:
        return default
    if text.lower().startswith("0x"):
        return int(text, 16)
    if text.lower().startswith("0b"):
        return int(text, 2)
    if all(c in "01-?xX" for c in text) and len(text) > 1:
        return int("".join("0" if c in "-?xX" else c for c in text), 2)
    return int(text, 10)


def sanitize_identifier(name: str, fallback: str = "UNNAMED") -> str:
    value = _IDENTIFIER.sub("_", (name or fallback).strip())
    value = re.sub(r"_+", "_", value).strip("_") or fallback
    if value[0].isdigit():
        value = f"_{value}"
    return value


def infer_access(raw: str | None) -> str:
    if not raw:
        return "read-write"
    text = raw.strip().lower().replace("_", "-")
    if "writeonly" in text or text in {"w", "wo", "write-only"}:
        return "write-only"
    if "readonly" in text or text in {"r", "ro", "read-only"}:
        return "read-only"

    # Microchip EDC uses one access character per bit. "n" means a normal
    # readable/writable bit, while "r" and "w" are restricted bits.
    bit_access = {char for char in text if char in {"n", "r", "w"}}
    if bit_access and bit_access <= {"r"}:
        return "read-only"
    if bit_access and bit_access <= {"w"}:
        return "write-only"
    return "read-write"


def reset_from_pattern(pattern: str | None, width: int) -> tuple[int, int]:
    if not pattern:
        mask = (1 << width) - 1
        return 0, mask
    text = pattern.strip().replace("_", "")
    if text.lower().startswith("0x"):
        mask = (1 << width) - 1
        return int(text, 16) & mask, mask
    bits = text[-width:].rjust(width, "-")
    value = 0
    known_mask = 0
    for index, char in enumerate(reversed(bits)):
        if char in "01":
            known_mask |= 1 << index
            if char == "1":
                value |= 1 << index
    return value, known_mask
