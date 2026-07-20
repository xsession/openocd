from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable
from xml.etree import ElementTree as ET


EXPECTED_DEVICES = {
    "dspic30f5011": "platforms/cpus/microchip/dspic30f5011.repl",
    "dspic33fj128mc802": "platforms/cpus/microchip/dspic33fj128mc802.repl",
    "dspic33fj128mc804": "platforms/cpus/microchip/dspic33fj128mc804.repl",
    "dspic33ep128gm604": "platforms/cpus/microchip/dspic33ep128gm604.repl",
}

CORE_PATH = Path("src/Infrastructure/src/Emulator/Cores/dsPIC33/dsPIC33.cs")
REGISTERS_PATH = Path("src/Infrastructure/src/Emulator/Cores/dsPIC33/dsPIC33Registers.cs")


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class AddressRange:
    name: str
    start: int
    end: int
    source: str

    def contains(self, address: int, width_bytes: int = 1) -> bool:
        return self.start <= address and address + width_bytes <= self.end


_HEX = r"0x[0-9A-Fa-f]+"
_RANGE_RE = re.compile(
    rf"(?P<name>[A-Za-z_][\w.-]*)\s*:\s*[^\n]+?@\s*sysbus\s*"
    rf"<\s*(?P<base>{_HEX})\s*,\s*\+(?P<size>{_HEX})\s*>",
    re.MULTILINE,
)
_MEMORY_RE = re.compile(
    rf"(?P<name>[A-Za-z_][\w.-]*)\s*:\s*Memory\.MappedMemory\s*@\s*sysbus\s*"
    rf"(?P<base>{_HEX})(?P<body>.*?)(?=\n\S|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SIZE_RE = re.compile(rf"\bsize\s*:\s*(?P<size>{_HEX})")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_repl_ranges(path: Path) -> list[AddressRange]:
    text = _read(path)
    if text is None:
        return []

    ranges: list[AddressRange] = []
    for match in _RANGE_RE.finditer(text):
        base = int(match.group("base"), 16)
        size = int(match.group("size"), 16)
        ranges.append(AddressRange(match.group("name"), base, base + size, str(path)))

    for match in _MEMORY_RE.finditer(text):
        size_match = _SIZE_RE.search(match.group("body"))
        if not size_match:
            continue
        base = int(match.group("base"), 16)
        size = int(size_match.group("size"), 16)
        ranges.append(AddressRange(match.group("name"), base, base + size, str(path)))

    return ranges


def svd_registers(path: Path) -> list[tuple[str, int, int]]:
    root = ET.parse(path).getroot()
    result: list[tuple[str, int, int]] = []
    for peripheral in root.findall("./peripherals/peripheral"):
        base = int(peripheral.findtext("baseAddress", "0"), 0)
        for register in peripheral.findall("./registers/register"):
            name = register.findtext("name", "<unnamed>")
            offset = int(register.findtext("addressOffset", "0"), 0)
            size_bits = int(register.findtext("size", root.findtext("width", "16")), 0)
            result.append((name, base + offset, max(1, (size_bits + 7) // 8)))
    return result


def validate_renode_tree(root: Path, svd_dir: Path | None = None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    build = root / "build.sh"
    build_text = _read(build)
    if build_text is None:
        diagnostics.append(Diagnostic("error", "RENODE_BUILD_MISSING", "build.sh is missing", str(build)))
    elif "dspic33.le" not in build_text:
        diagnostics.append(
            Diagnostic("error", "RENODE_TLIB_NOT_BUILT", "build.sh does not include dspic33.le", str(build))
        )

    core = root / CORE_PATH
    core_text = _read(core)
    if core_text is None:
        diagnostics.append(Diagnostic("error", "RENODE_CORE_MISSING", "dsPIC33 CPU core is missing", str(core)))
    else:
        for needle, code, message in (
            ('Architecture => "dspic33"', "RENODE_ARCH", "CPU Architecture is not dspic33"),
            ('GDBArchitecture => "dspic33"', "RENODE_GDB_ARCH", "GDB architecture is not dspic33"),
        ):
            if needle not in core_text:
                diagnostics.append(Diagnostic("error", code, message, str(core)))
        if re.search(r"GDBFeatures\s*=>\s*\n?\s*new List<GDBFeatureDescriptor>\(\)", core_text):
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "RENODE_EMPTY_GDB_FEATURES",
                    "The dsPIC33 core exposes no GDB target-description features; test the selected GDB client explicitly.",
                    str(core),
                )
            )
        if re.search(r"FindBestInterrupt\(\).*?return\s+0\s*;", core_text, re.DOTALL):
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "RENODE_INTERRUPT_STUB",
                    "FindBestInterrupt is a stub returning interrupt 0; interrupt-driven firmware is not production-ready.",
                    str(core),
                )
            )

    registers = root / REGISTERS_PATH
    registers_text = _read(registers)
    if registers_text is None:
        diagnostics.append(
            Diagnostic("error", "RENODE_REGISTERS_MISSING", "dsPIC33 GDB register map is missing", str(registers))
        )
    else:
        required = ("W0", "W15", "PC", "STATUS")
        for name in required:
            if not re.search(rf"dsPIC33Registers\.{name}\b", registers_text):
                diagnostics.append(
                    Diagnostic("error", "RENODE_REGISTER_MISSING", f"GDB register map lacks {name}", str(registers))
                )

    platform_ranges: dict[str, list[AddressRange]] = {}
    for device, relative in EXPECTED_DEVICES.items():
        path = root / relative
        if not path.exists():
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "RENODE_PLATFORM_MISSING",
                    f"No exact Renode platform description for {device}.",
                    str(path),
                )
            )
            continue
        text = _read(path) or ""
        if "CPU.DSPIC33" not in text:
            diagnostics.append(
                Diagnostic("error", "RENODE_PLATFORM_CPU", f"{device} platform does not instantiate CPU.DSPIC33", str(path))
            )
        platform_ranges[device] = parse_repl_ranges(path)

    # The branch currently carries a similarly named GM802 platform. Explicitly flag it so it is
    # never silently treated as the requested MC802 device.
    near_match = root / "platforms/cpus/microchip/dspic33fj128gm802.repl"
    if not (root / EXPECTED_DEVICES["dspic33fj128mc802"]).exists() and near_match.exists():
        diagnostics.append(
            Diagnostic(
                "warning",
                "RENODE_NEAR_MATCH_ONLY",
                "dspic33fj128gm802.repl exists, but it is not an exact model for dsPIC33FJ128MC802.",
                str(near_match),
            )
        )

    if svd_dir is not None:
        for device, ranges in platform_ranges.items():
            svd = svd_dir / f"{device}.svd"
            if not svd.exists():
                continue
            registers_in_svd = svd_registers(svd)
            if not registers_in_svd:
                diagnostics.append(Diagnostic("error", "SVD_EMPTY", f"{svd.name} has no registers", str(svd)))
                continue
            covered = [item for item in registers_in_svd if any(r.contains(item[1], item[2]) for r in ranges)]
            diagnostics.append(
                Diagnostic(
                    "info",
                    "RENODE_SVD_COVERAGE",
                    f"{device}: {len(covered)}/{len(registers_in_svd)} SVD registers fall inside explicitly mapped Renode ranges.",
                    str(svd),
                )
            )

    return diagnostics


def diagnostics_exit_code(diagnostics: Iterable[Diagnostic], strict: bool = False) -> int:
    severities = {d.severity for d in diagnostics}
    if "error" in severities:
        return 1
    if strict and "warning" in severities:
        return 2
    return 0
