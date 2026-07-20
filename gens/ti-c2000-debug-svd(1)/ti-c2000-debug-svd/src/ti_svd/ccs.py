from __future__ import annotations

import fnmatch
import os
import platform
from pathlib import Path

from .models import DeviceManifest


def candidate_ccs_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("CCS_ROOT", "TI_CCS_ROOT", "CCSTUDIO_ROOT"):
        if os.environ.get(env_name):
            candidates.append(Path(os.environ[env_name]))
    system = platform.system()
    if system == "Windows":
        for drive in ("C:", "D:"):
            candidates.extend([
                Path(drive) / "ti",
                Path(drive) / "Program Files" / "Texas Instruments",
                Path(drive) / "Program Files (x86)" / "Texas Instruments",
            ])
    else:
        candidates.extend([Path.home() / "ti", Path("/opt/ti"), Path("/usr/local/ti")])
    unique: list[Path] = []
    for path in candidates:
        path = path.expanduser()
        if path.exists() and path not in unique:
            unique.append(path)
    return unique


def find_targetdb_roots(ccs_root: Path | None = None) -> list[Path]:
    search_roots = [ccs_root] if ccs_root else candidate_ccs_roots()
    found: list[Path] = []
    for root in search_roots:
        if root is None or not root.exists():
            continue
        direct_candidates = [
            root / "ccs" / "ccs_base" / "common" / "targetdb",
            root / "ccs_base" / "common" / "targetdb",
            root / "common" / "targetdb",
            root,
        ]
        direct_found = False
        for candidate in direct_candidates:
            if (candidate / "devices").is_dir() and (candidate / "Modules").is_dir():
                direct_found = True
                if candidate not in found:
                    found.append(candidate)
        if direct_found:
            continue
        for devices in root.glob("**/ccs_base/common/targetdb/devices"):
            targetdb = devices.parent
            if (targetdb / "Modules").is_dir() and targetdb not in found:
                found.append(targetdb)
    return found


def score_device_xml(path: Path, manifest: DeviceManifest) -> tuple[int, int, str]:
    name = path.name.upper()
    score = 0
    exact = manifest.name.upper() + ".XML"
    if name == exact:
        score += 1000
    compact_id = manifest.id.replace("_", "").upper()
    compact_name = name.replace("_", "")
    if compact_id in compact_name:
        score += 400
    for token in manifest.include_tokens:
        if token in name or token in str(path.parent).upper():
            score += 30
    for token in manifest.exclude_tokens:
        if token in name or token in str(path.parent).upper():
            score -= 100
    return score, -len(str(path)), str(path)


def find_device_xml(targetdb: Path, manifest: DeviceManifest) -> list[Path]:
    devices = targetdb / "devices"
    matches: list[Path] = []
    all_xml = list(devices.rglob("*.xml")) + list(devices.rglob("*.XML"))
    for pattern in manifest.device_xml_patterns:
        pattern_lower = pattern.lower()
        for path in all_xml:
            if fnmatch.fnmatch(path.name.lower(), pattern_lower) and path not in matches:
                matches.append(path)
    return sorted(matches, key=lambda p: score_device_xml(p, manifest), reverse=True)
