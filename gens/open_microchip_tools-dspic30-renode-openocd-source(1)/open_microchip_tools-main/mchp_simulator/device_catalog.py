from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class DeviceSpec:
    name: str
    family: str
    program_bytes: int
    data_bytes: int
    instruction_bytes: int
    pc_start: int = 0


_DSPIC33_FLASH_KB_RE = re.compile(r"(?:dsPIC33\w*?)(512|256|128|64|32|16)")


def _guess_dspic33_program_bytes(name: str) -> int:
    m = _DSPIC33_FLASH_KB_RE.search(name)
    if not m:
        # Conservative default to keep the simulator usable.
        return 256 * 1024
    return int(m.group(1)) * 1024


def guess_device_spec(name: str) -> DeviceSpec:
    n = (name or "").strip()
    if not n:
        return DeviceSpec(
            name="UNKNOWN",
            family="OTHER",
            program_bytes=0x10000,
            data_bytes=0x10000,
            instruction_bytes=2,
        )

    if n.lower().startswith("dspic33"):
        return DeviceSpec(
            name=n,
            family="dsPIC33",
            program_bytes=_guess_dspic33_program_bytes(n),
            data_bytes=0x10000,
            instruction_bytes=2,
        )

    if n.lower().startswith("dspic30"):
        # dsPIC30 devices are also word/instruction addressed; keep the MVP consistent
        # with dsPIC33 for stepping/trace.
        return DeviceSpec(
            name=n,
            family="dsPIC30",
            program_bytes=0x10000,
            data_bytes=0x10000,
            instruction_bytes=2,
        )

    # Generic fallback for all other parts we can list but don't yet model.
    return DeviceSpec(
        name=n,
        family="OTHER",
        program_bytes=0x10000,
        data_bytes=0x10000,
        instruction_bytes=1,
    )


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _default_pm3socketinfo_path() -> str:
    return os.path.join(
        _repo_root(),
        "_mplab_sys",
        "mplab_ipe",
        "src",
        "modules",
        "com",
        "microchip",
        "mplab",
        "ipelib",
        "device",
        "pm3socketinfo.xml",
    )


@lru_cache(maxsize=1)
def available_device_names(source_path: Optional[str] = None) -> List[str]:
    """Return device names known to the repo.

    Today this is sourced from MPLAB IPE's `pm3socketinfo.xml` snapshot, which
    contains a large cross-family list of device names.
    """

    path = source_path or _default_pm3socketinfo_path()
    if not os.path.exists(path):
        return [
            "dsPIC33EP512GM710",
            "dsPIC33EP256GM304",
            "dsPIC33CH128MP202",
        ]

    tree = ET.parse(path)
    root = tree.getroot()

    names: List[str] = []
    for dev in root.iter():
        if dev.tag.endswith("Device"):
            name = dev.attrib.get("name")
            if name:
                names.append(name.strip())

    # De-dup while preserving order.
    seen = set()
    out: List[str] = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def available_devices(prefix: Optional[str] = None) -> List[DeviceSpec]:
    names = available_device_names()
    if prefix:
        p = prefix.lower()
        names = [n for n in names if n.lower().startswith(p)]
    return [guess_device_spec(n) for n in names]
