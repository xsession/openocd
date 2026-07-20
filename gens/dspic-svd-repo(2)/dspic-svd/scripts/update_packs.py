#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tomllib
import urllib.request
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from common import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd import __version__  # noqa: E402
from dspic_svd.convert import convert_file  # noqa: E402
from dspic_svd.cortex_debug import validate_cortex_debug_file  # noqa: E402
from dspic_svd.validate import validate_file  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict:
    with (ROOT / "packs.toml").open("rb") as handle:
        return tomllib.load(handle)


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": f"dspic-svd/{__version__}"})
    print(f"download {url}")
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    partial.replace(target)


def descriptor_stems(device: str) -> set[str]:
    target = device.lower()
    stems = {target}
    if target.startswith("dspic"):
        stems.add("p" + target.removeprefix("dspic"))
    return stems


def find_member(archive: ZipFile, device: str) -> str:
    stems = descriptor_stems(device)
    candidates = []
    for name in archive.namelist():
        base = Path(name).name.lower()
        stem = Path(base).stem
        suffix = Path(base).suffix.lower()
        if suffix not in {".pic", ".atdf"}:
            continue
        if stem in stems:
            candidates.append(name)
    if not candidates:
        for name in archive.namelist():
            base = Path(name).name.lower()
            if any(target in base for target in stems) and Path(base).suffix.lower() in {
                ".pic",
                ".atdf",
            }:
                candidates.append(name)
    if not candidates:
        raise FileNotFoundError(f"device descriptor for {device} not found in pack")
    candidates.sort(key=lambda name: (0 if name.lower().endswith(".atdf") else 1, len(name)))
    return candidates[0]


def process_pack(pack: dict, archive_path: Path) -> None:
    try:
        archive = ZipFile(archive_path)
    except BadZipFile as exc:
        raise SystemExit(f"invalid atpack/zip: {archive_path}: {exc}") from exc
    with archive:
        for device in pack["devices"]:
            member = find_member(archive, device)
            suffix = Path(member).suffix
            source_path = ROOT / "sources" / f"{device}{suffix}"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, source_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            output_path = ROOT / "svd" / f"{device.lower()}.svd"
            model = convert_file(source_path, output_path, device)
            structural_errors = validate_file(output_path)
            cortex_debug_errors = validate_cortex_debug_file(output_path)
            if structural_errors or cortex_debug_errors:
                details = "\n".join(
                    f"  - {error}" for error in [*structural_errors, *cortex_debug_errors]
                )
                raise SystemExit(f"generated SVD validation failed for {device}:\n{details}")
            metadata = {
                "device": device,
                "pack": pack["name"],
                "pack_version": pack["version"],
                "pack_url": pack["url"],
                "pack_sha256": sha256(archive_path),
                "source_member": member,
                "source_sha256": sha256(source_path),
                "raw_svd_sha256": sha256(output_path),
                "svd_sha256": sha256(output_path),
                "converter_version": __version__,
                "cmsis_svd_valid": True,
                "cortex_debug_compatible": True,
                "register_count": len(model.registers),
                "field_count": sum(len(reg.fields) for reg in model.registers),
            }
            metadata_path = ROOT / "metadata" / f"{device.lower()}.json"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            print(
                f"generated {output_path.relative_to(ROOT)} from {member}: "
                f"{metadata['register_count']} registers, {metadata['field_count']} fields"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Microchip packs and generate selected dsPIC SVDs"
    )
    parser.add_argument("--pack-file", action="append", type=Path, default=[])
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    supplied = {path.name: path for path in args.pack_file}
    cache = ROOT / ".cache" / "packs"
    for pack in manifest["packs"]:
        expected_name = Path(pack["url"]).name
        archive_path = supplied.get(expected_name)
        if archive_path is None:
            matches = [p for p in args.pack_file if pack["name"].lower() in p.name.lower()]
            archive_path = matches[0] if matches else cache / expected_name
        if not archive_path.exists():
            if args.offline:
                raise SystemExit(f"missing cached pack in offline mode: {archive_path}")
            download(pack["url"], archive_path)
        elif args.force and archive_path.parent == cache and not args.offline:
            download(pack["url"], archive_path)
        process_pack(pack, archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
