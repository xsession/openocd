from __future__ import annotations

import gzip
import json
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


TOOL_PACK_NAMES: Dict[str, str] = {
    "pk4": "PICkit4_TP",
    "icd4": "ICD4_TP",
    "pickit4": "PICkit4_TP",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def vendor_root() -> Path:
    return repo_root() / "vendor" / "mplabx"


def vendor_yaml_root() -> Path:
    return repo_root() / "vendor" / "mplabx_yaml_gz"


def vendor_firmware_root() -> Path:
    return vendor_root() / "tool_firmware"


def vendor_packs_root() -> Path:
    return vendor_root() / "packs" / "Microchip"


def manifest_path() -> Path:
    return vendor_root() / "asset_manifest.json"


_JAM_NAME_RE = re.compile(r"(?P<name>[A-Za-z0-9_\-]+)_(?P<version>[0-9A-Fa-f]{6})\.jam$", re.IGNORECASE)
_COMPRESSIBLE_SUFFIXES = {".xml", ".pic"}


def normalize_tool(tool: str) -> str:
    normalized = str(tool).strip().lower()
    if normalized not in TOOL_PACK_NAMES:
        raise ValueError(f"Unsupported tool '{tool}'")
    return normalized


def tool_pack_name(tool: str) -> str:
    return TOOL_PACK_NAMES[normalize_tool(tool)]


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _version_key(name: str) -> Tuple[Tuple[int, object], ...]:
    parts: List[Tuple[int, object]] = []
    for part in name.replace("-", ".").split("."):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part.lower()))
    return tuple(parts)


def _latest_version_dir(pack_dir: Path) -> Optional[Path]:
    if not pack_dir.exists():
        return None
    versions = [child for child in pack_dir.iterdir() if child.is_dir()]
    if not versions:
        return None
    return sorted(versions, key=lambda path: _version_key(path.name))[-1]


def _compressed_storage_path(path: Path) -> Path:
    if path.suffix.lower() not in _COMPRESSIBLE_SUFFIXES:
        return path
    return path.with_suffix(path.suffix + ".gz")


def _resolve_xml_storage_path(path: Path) -> Optional[Path]:
    compressed = _compressed_storage_path(path)
    if compressed.exists():
        return compressed
    if path.exists():
        return path
    return None


def _parse_xml_root(path: Path) -> ET.Element:
    stored_path = _resolve_xml_storage_path(path)
    if stored_path is None:
        raise FileNotFoundError(path)
    if stored_path.suffix.lower() == ".gz":
        with gzip.open(stored_path, "rb") as handle:
            return ET.parse(handle).getroot()
    return ET.parse(stored_path).getroot()


def resolve_repo_scripts_path(tool: str, *, base: Optional[Path] = None) -> Optional[Path]:
    packs_base = (base or vendor_packs_root())
    pack_dir = packs_base / tool_pack_name(tool)
    version_dir = _latest_version_dir(pack_dir)
    if version_dir is not None:
        candidate = version_dir / "firmware" / "scripts.xml"
        resolved = _resolve_xml_storage_path(candidate)
        if resolved is not None:
            return resolved
        for yaml_name in ("scripts.yaml.gz", "scripts.yaml"):
            yaml_candidate = version_dir / "firmware" / yaml_name
            if yaml_candidate.exists():
                return yaml_candidate

    if base is None:
        yaml_pack_dir = vendor_yaml_root() / "packs" / "Microchip" / tool_pack_name(tool)
        yaml_version_dir = _latest_version_dir(yaml_pack_dir)
        if yaml_version_dir is not None:
            for yaml_name in ("scripts.yaml.gz", "scripts.yaml"):
                yaml_candidate = yaml_version_dir / "firmware" / yaml_name
                if yaml_candidate.exists():
                    return yaml_candidate
    return None


def resolve_repo_device_file(processor: str, *, base: Optional[Path] = None) -> Optional[Path]:
    packs_base = (base or vendor_packs_root())
    pattern = f"*/ */edc/{processor}.PIC*"
    for candidate in packs_base.glob(pattern.replace(" ", "")):
        resolved = _resolve_xml_storage_path(candidate)
        if resolved is not None:
            return resolved
    yaml_pattern = f"*/ */edc/{processor}.yaml*"
    for candidate in packs_base.glob(yaml_pattern.replace(" ", "")):
        if candidate.exists():
            return candidate
    if base is None:
        yaml_base = vendor_yaml_root() / "packs" / "Microchip"
        for candidate in yaml_base.glob(yaml_pattern.replace(" ", "")):
            if candidate.exists():
                return candidate
    return None


def _parse_jam_filename(path: Path) -> Tuple[str, str]:
    match = _JAM_NAME_RE.match(path.name)
    if match is None:
        return path.stem, ""
    return match.group("name"), match.group("version").upper()


def resolve_repo_firmware_path(tool: str, *, base: Optional[Path] = None) -> Optional[Path]:
    if base is None:
        canonical_root = vendor_firmware_root() / normalize_tool(tool)
        canonical_jams = sorted(canonical_root.glob("*.jam"))
        if canonical_jams:
            return canonical_jams[0]
    packs_base = (base or vendor_packs_root())
    pack_dir = packs_base / tool_pack_name(tool)
    version_dir = _latest_version_dir(pack_dir)
    if version_dir is None:
        return None
    jams = sorted((version_dir / "firmware").glob("*.jam"))
    if not jams:
        return None
    return jams[0]


def iter_repo_firmware_packages(*, base: Optional[Path] = None) -> List[Dict[str, str]]:
    packs_base = base or vendor_packs_root()
    packages: List[Dict[str, str]] = []
    for tool, pack_name in sorted(TOOL_PACK_NAMES.items()):
        if tool not in {"pk4", "icd4"}:
            continue
        version_dir = _latest_version_dir(packs_base / pack_name)
        if version_dir is None:
            continue
        for jam in sorted((version_dir / "firmware").glob("*.jam")):
            image_name, version = _parse_jam_filename(jam)
            packages.append(
                {
                    "tool": tool.upper(),
                    "pack": pack_name,
                    "toolVersion": version_dir.name,
                    "imageName": image_name,
                    "firmwareVersion": version,
                    "path": str(jam),
                }
            )
    return packages


def load_manifest(path: Optional[Path] = None) -> Dict[str, object]:
    manifest = path or manifest_path()
    if not manifest.exists():
        return {"toolpacks": {}, "devicePacks": {}}
    return json.loads(manifest.read_text(encoding="utf-8"))


def save_manifest(data: Dict[str, object], path: Optional[Path] = None) -> None:
    manifest = path or manifest_path()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _copy_file(src: Path, dst: Path) -> str:
    actual_dst = _compressed_storage_path(dst)
    actual_dst.parent.mkdir(parents=True, exist_ok=True)
    stale_paths = [actual_dst]
    if actual_dst != dst:
        stale_paths.append(dst)
    for stale_path in stale_paths:
        if not stale_path.exists():
            continue
        try:
            stale_path.chmod(0o666)
        except Exception:
            pass
        try:
            stale_path.unlink()
        except Exception:
            pass
    if src.suffix.lower() in _COMPRESSIBLE_SUFFIXES and dst.suffix.lower() in _COMPRESSIBLE_SUFFIXES:
        with src.open("rb") as source_handle, gzip.open(actual_dst, "wb", compresslevel=9) as target_handle:
            shutil.copyfileobj(source_handle, target_handle)
        return str(actual_dst)
    shutil.copy2(src, actual_dst)
    return str(actual_dst)


def _copy_optional_files(src_root: Path, dst_root: Path, relative_paths: Iterable[str]) -> List[str]:
    copied: List[str] = []
    for rel in relative_paths:
        src = src_root / rel
        if not src.exists():
            continue
        copied.append(_copy_file(src, dst_root / rel))
    return copied


def _copy_tree(src: Path, dst: Path) -> List[str]:
    copied: List[str] = []
    if not src.exists():
        return copied
    for child in src.rglob("*"):
        if child.is_dir():
            continue
        rel = child.relative_to(src)
        copied.append(_copy_file(child, dst / rel))
    return copied


def _mirror_tool_firmware(tool: str, tool_pack_dir: Path, destination_root: Path) -> List[str]:
    mirrored: List[str] = []
    firmware_dst = destination_root / normalize_tool(tool)
    for jam in sorted((tool_pack_dir / "firmware").glob("*.jam")):
        mirrored.append(_copy_file(jam, firmware_dst / jam.name))
    for payload_name in ("app.hex", "boot.hex"):
        payload = tool_pack_dir / "firmware" / payload_name
        if payload.exists():
            mirrored.append(_copy_file(payload, firmware_dst / payload_name))
    return mirrored


def _find_device_pack_dir(mplab_packs_root: Path, processor: str) -> Optional[Tuple[Path, Path]]:
    for pic_path in mplab_packs_root.glob(f"*/*/edc/{processor}.PIC"):
        if pic_path.is_file():
            return pic_path.parents[1], pic_path
    return None


def _index_device_files(mplab_packs_root: Path) -> Dict[str, Path]:
    index: Dict[str, Path] = {}
    for pic_path in mplab_packs_root.glob("*/*/edc/*.PIC"):
        if not pic_path.is_file():
            continue
        index.setdefault(pic_path.stem.lower(), pic_path)
    return index


def supported_processors_from_device_support(path: Path, tool: str) -> Set[str]:
    normalized_tool = normalize_tool(tool)
    root = _parse_xml_root(path)
    support_attrs = (f"{normalized_tool}d", f"{normalized_tool}p")
    supported: Set[str] = set()
    for device in root.iter():
        if _local_name(device.tag) != "device":
            continue
        device_name = next((value for key, value in device.attrib.items() if _local_name(key) == "name"), "").strip()
        if not device_name:
            continue
        for child in list(device):
            if _local_name(child.tag) != "support":
                continue
            values = [str(value).strip().lower() for key, value in child.attrib.items() if _local_name(key) in support_attrs]
            if any(value and value != "no" for value in values):
                supported.add(device_name)
                break
    return supported


def supported_family_packs(mplab_root: Path, tools: Sequence[str]) -> Dict[str, object]:
    packs_root = mplab_root / "packs" / "Microchip"
    device_index = _index_device_files(packs_root)
    supported_processors: Dict[str, Set[str]] = {}
    matched_pack_dirs: Dict[Tuple[str, str], Path] = {}

    for tool in tools:
        pack_dir = _latest_version_dir(packs_root / tool_pack_name(tool))
        if pack_dir is None:
            raise FileNotFoundError(f"Tool pack not found for {tool}")
        support_path = pack_dir / "device_support.xml"
        processors = supported_processors_from_device_support(support_path, tool)
        supported_processors[normalize_tool(tool).upper()] = processors
        for processor in processors:
            pic_path = device_index.get(processor.lower())
            if pic_path is None:
                continue
            pack_dir = pic_path.parents[1]
            matched_pack_dirs[(pack_dir.parent.name, pack_dir.name)] = pack_dir

    pack_entries = [
        {
            "pack": pack_name,
            "version": version,
            "sourcePath": str(path),
        }
        for (pack_name, version), path in sorted(matched_pack_dirs.items())
    ]
    return {
        "tools": {tool: sorted(processors) for tool, processors in supported_processors.items()},
        "packs": pack_entries,
    }


@dataclass(frozen=True)
class CollectedAssets:
    tool: str
    tool_pack: str
    tool_version: str
    scripts_path: str
    copied_files: Tuple[str, ...]
    device_pack: Optional[str] = None
    device_version: Optional[str] = None
    processor: Optional[str] = None
    device_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        result: Dict[str, object] = {
            "tool": self.tool,
            "toolPack": self.tool_pack,
            "toolVersion": self.tool_version,
            "scriptsPath": self.scripts_path,
            "copiedFiles": list(self.copied_files),
        }
        if self.device_pack is not None:
            result["devicePack"] = self.device_pack
        if self.device_version is not None:
            result["deviceVersion"] = self.device_version
        if self.processor is not None:
            result["processor"] = self.processor
        if self.device_file_path is not None:
            result["deviceFilePath"] = self.device_file_path
        return result


def collect_repo_assets(
    *,
    mplab_root: Path,
    tool: str,
    processor: Optional[str] = None,
    destination_root: Optional[Path] = None,
) -> CollectedAssets:
    packs_root = mplab_root / "packs" / "Microchip"
    if not packs_root.exists():
        raise FileNotFoundError(f"MPLAB packs root not found: {packs_root}")

    destination = destination_root or vendor_root()
    packs_destination = destination / "packs" / "Microchip"
    firmware_destination = destination / "tool_firmware"

    normalized_tool = normalize_tool(tool)
    tool_pack = tool_pack_name(normalized_tool)
    tool_pack_dir = _latest_version_dir(packs_root / tool_pack)
    if tool_pack_dir is None:
        raise FileNotFoundError(f"Tool pack not found for {tool_pack}")

    tool_destination = packs_destination / tool_pack / tool_pack_dir.name
    copied_files = _copy_optional_files(
        tool_pack_dir,
        tool_destination,
        (
            "firmware/PK4FW_001000.jam",
            "firmware/ICD4FW_001000.jam",
            "firmware/app.hex",
            "firmware/boot.hex",
            "firmware/scripts.xml",
            "firmware/scripts-v2.zip",
            "firmware/ptg/ToolInfo",
            "firmware/Pk4HybridTooImpl.toolMediator",
            "device_support.xml",
            "pickit4.xml",
            f"Microchip.{tool_pack}.pdsc",
        ),
    )
    copied_files.extend(_mirror_tool_firmware(normalized_tool, tool_pack_dir, firmware_destination))

    device_pack = None
    device_version = None
    device_file_path = None
    if processor:
        found = _find_device_pack_dir(packs_root, processor)
        if found is None:
            raise FileNotFoundError(f"Device pack not found for processor '{processor}'")
        device_pack_dir, pic_path = found
        device_pack = device_pack_dir.parent.name
        device_version = device_pack_dir.name
        device_destination = packs_destination / device_pack / device_version
        copied_files.extend(
            _copy_optional_files(
                device_pack_dir,
                device_destination,
                (
                    f"edc/{processor}.PIC",
                    f"Microchip.{device_pack}.pdsc",
                    f"Microchip.{device_pack}.sha1",
                ),
            )
        )
        device_file_path = str(_compressed_storage_path(device_destination / "edc" / f"{processor}.PIC"))

    scripts_path = str(_compressed_storage_path(tool_destination / "firmware" / "scripts.xml"))
    manifest = load_manifest(destination / "asset_manifest.json")
    toolpacks = dict(manifest.get("toolpacks", {}))
    toolpacks[normalized_tool.upper()] = {
        "pack": tool_pack,
        "version": tool_pack_dir.name,
        "scriptsPath": scripts_path,
        "firmwarePath": str(resolve_repo_firmware_path(normalized_tool, base=packs_destination) or ""),
    }
    manifest["toolpacks"] = toolpacks

    if processor:
        device_packs = dict(manifest.get("devicePacks", {}))
        device_packs[processor] = {
            "pack": device_pack,
            "version": device_version,
            "deviceFilePath": device_file_path,
        }
        manifest["devicePacks"] = device_packs

    save_manifest(manifest, destination / "asset_manifest.json")

    return CollectedAssets(
        tool=normalized_tool.upper(),
        tool_pack=tool_pack,
        tool_version=tool_pack_dir.name,
        scripts_path=scripts_path,
        copied_files=tuple(copied_files),
        device_pack=device_pack,
        device_version=device_version,
        processor=processor,
        device_file_path=device_file_path,
    )


def collect_supported_family_packs(
    *,
    mplab_root: Path,
    tools: Sequence[str],
    destination_root: Optional[Path] = None,
) -> Dict[str, object]:
    packs_root = mplab_root / "packs" / "Microchip"
    destination = destination_root or vendor_root()
    packs_destination = destination / "packs" / "Microchip"
    firmware_destination = destination / "tool_firmware"

    summary = supported_family_packs(mplab_root, tools)
    copied_toolpacks: List[Dict[str, object]] = []
    copied_packs: List[Dict[str, object]] = []

    manifest = load_manifest(destination / "asset_manifest.json")
    toolpacks_manifest = dict(manifest.get("toolpacks", {}))
    family_packs_manifest = dict(manifest.get("familyPacks", {}))

    for tool in tools:
        normalized_tool = normalize_tool(tool)
        pack_name = tool_pack_name(normalized_tool)
        version_dir = _latest_version_dir(packs_root / pack_name)
        if version_dir is None:
            raise FileNotFoundError(f"Tool pack not found for {tool}")
        tool_dst = packs_destination / pack_name / version_dir.name
        copied_files = _copy_optional_files(
            version_dir,
            tool_dst,
            (
                "firmware/PK4FW_001000.jam",
                "firmware/ICD4FW_001000.jam",
                "firmware/app.hex",
                "firmware/boot.hex",
                "firmware/scripts.xml",
                "firmware/scripts-v2.zip",
                "firmware/ptg/ToolInfo",
                "firmware/Pk4HybridTooImpl.toolMediator",
                "device_support.xml",
                "pickit4.xml",
                "icd4.xml",
                f"Microchip.{pack_name}.pdsc",
            ),
        )
        copied_files.extend(_mirror_tool_firmware(normalized_tool, version_dir, firmware_destination))
        scripts_path = str(_compressed_storage_path(tool_dst / "firmware" / "scripts.xml"))
        toolpacks_manifest[normalized_tool.upper()] = {
            "pack": pack_name,
            "version": version_dir.name,
            "scriptsPath": scripts_path,
            "firmwarePath": str(resolve_repo_firmware_path(normalized_tool, base=packs_destination) or ""),
        }
        copied_toolpacks.append(
            {
                "tool": normalized_tool.upper(),
                "pack": pack_name,
                "version": version_dir.name,
                "scriptsPath": scripts_path,
                "firmwarePath": str(resolve_repo_firmware_path(normalized_tool, base=packs_destination) or ""),
                "copiedFiles": copied_files,
            }
        )

    for entry in summary["packs"]:
        source = Path(str(entry["sourcePath"]))
        pack_name = str(entry["pack"])
        version = str(entry["version"])
        dst = packs_destination / pack_name / version
        copied_files = _copy_tree(source / "edc", dst / "edc")
        copied_files.extend(
            _copy_optional_files(
                source,
                dst,
                (
                    f"Microchip.{pack_name}.pdsc",
                    f"Microchip.{pack_name}.sha1",
                ),
            )
        )
        family_packs_manifest[f"{pack_name}@{version}"] = {
            "pack": pack_name,
            "version": version,
            "edcPath": str(dst / "edc"),
        }
        copied_packs.append(
            {
                "pack": pack_name,
                "version": version,
                "copiedFileCount": len(copied_files),
                "edcPath": str(dst / "edc"),
            }
        )

    manifest["toolpacks"] = toolpacks_manifest
    manifest["firmwarePackages"] = iter_repo_firmware_packages(base=packs_destination)
    manifest["familyPacks"] = family_packs_manifest
    manifest["supportedByTool"] = {
        tool: {
            "processorCount": len(processors),
            "processors": processors,
        }
        for tool, processors in summary["tools"].items()
    }
    save_manifest(manifest, destination / "asset_manifest.json")

    return {
        "tools": list(dict.fromkeys(normalize_tool(tool).upper() for tool in tools)),
        "toolpackCount": len(copied_toolpacks),
        "familyPackCount": len(copied_packs),
        "toolpacks": copied_toolpacks,
        "familyPacks": copied_packs,
        "supportedByTool": manifest["supportedByTool"],
    }