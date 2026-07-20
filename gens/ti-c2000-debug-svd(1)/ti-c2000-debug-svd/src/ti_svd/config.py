from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .models import DeviceManifest


def _is_repository_root(path: Path) -> bool:
    return (path / "devices").is_dir() and (path / "sources.lock.json").is_file()


def repository_root() -> Path:
    """Resolve the source repository containing device manifests.

    The editable-install/source-tree case is detected automatically. A regular
    wheel install can be used while the current directory is the cloned
    repository, or with TI_SVD_REPOSITORY_ROOT pointing at that repository.
    """
    override = os.environ.get("TI_SVD_REPOSITORY_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if not _is_repository_root(candidate):
            raise FileNotFoundError(
                f"TI_SVD_REPOSITORY_ROOT is not a ti-c2000-mspm0-svd repository: {candidate}"
            )
        return candidate

    candidates = [Path.cwd().resolve(), Path(__file__).resolve().parents[2]]
    for candidate in candidates:
        if _is_repository_root(candidate):
            return candidate

    raise FileNotFoundError(
        "cannot locate the ti-c2000-mspm0-svd repository; run from the cloned "
        "repository or set TI_SVD_REPOSITORY_ROOT"
    )


def load_manifest(device_id: str, root: Path | None = None) -> DeviceManifest:
    root = root or repository_root()
    path = root / "devices" / f"{device_id}.toml"
    if not path.exists():
        known = ", ".join(p.stem for p in sorted((root / "devices").glob("*.toml")))
        raise FileNotFoundError(f"unknown device '{device_id}'; available: {known}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = {
        "id", "name", "vendor", "family", "source", "output", "core",
        "address_unit_bits", "width", "address_scale", "default_register_width",
        "device_xml_patterns", "include_tokens", "exclude_tokens", "cortex_debug",
        "processor_name", "compatibility_note",
    }
    return DeviceManifest(
        id=data["id"],
        name=data["name"],
        vendor=data["vendor"],
        family=data["family"],
        source=data["source"],
        output=root / data["output"],
        core=data["core"],
        address_unit_bits=int(data.get("address_unit_bits", 8)),
        width=int(data.get("width", 32)),
        address_scale=int(data.get("address_scale", 1)),
        default_register_width=int(data.get("default_register_width", data.get("width", 32))),
        device_xml_patterns=list(data.get("device_xml_patterns", [])),
        include_tokens=[str(x).upper() for x in data.get("include_tokens", [])],
        exclude_tokens=[str(x).upper() for x in data.get("exclude_tokens", [])],
        cortex_debug=bool(data.get("cortex_debug", False)),
        processor_name=str(data.get("processor_name", "")),
        compatibility_note=str(data.get("compatibility_note", "")),
        extra={k: v for k, v in data.items() if k not in known},
    )


def list_manifests(root: Path | None = None) -> list[str]:
    root = root or repository_root()
    return [p.stem for p in sorted((root / "devices").glob("*.toml"))]
