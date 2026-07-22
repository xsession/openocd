#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Universal CMSIS-SVD helper for OpenOCD-supported targets.

This tool is a front door for SVD sources that already exist in or near the
OpenOCD tree. It validates committed SVD files, inventories target configs,
imports local CMSIS-Pack archives, and delegates TI generation to the existing
TI C2000/MSPM0 generator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = Path(__file__).with_name("sources.json")


@dataclass
class SvdInfo:
    path: Path
    name: str
    version: str
    description: str
    cpu: str
    address_unit_bits: int
    width: int
    peripheral_count: int
    register_count: int
    field_count: int
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _direct(parent: ET.Element, name: str) -> ET.Element | None:
    for child in list(parent):
        if _tag(child) == name:
            return child
    return None


def _direct_text(parent: ET.Element, name: str, default: str = "") -> str:
    child = _direct(parent, name)
    return (child.text or "").strip() if child is not None else default


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _tag(child) == name]


def _parse_int(value: str, default: int = 0) -> int:
    value = (value or "").strip()
    if not value:
        return default
    try:
        return int(value, 0)
    except ValueError:
        return default


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def load_sources() -> list[dict[str, object]]:
    return json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["sources"]


def iter_svd_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*.svd") if path.is_file())


def inspect_svd(path: Path) -> SvdInfo:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return SvdInfo(path, "", "", "", "", 8, 32, 0, 0, 0, warnings, [str(exc)])

    root = tree.getroot()
    if _tag(root) != "device":
        errors.append(f"root element is <{_tag(root)}> instead of <device>")

    name = _direct_text(root, "name")
    if not name:
        errors.append("missing <name>")

    version = _direct_text(root, "version")
    if not version:
        warnings.append("missing <version>")

    description = _direct_text(root, "description")
    if not description:
        warnings.append("missing <description>")

    address_unit_text = _direct_text(root, "addressUnitBits", "8")
    address_unit_bits = _parse_int(address_unit_text, 8)
    if address_unit_bits not in {8, 16, 32}:
        errors.append(f"unsupported <addressUnitBits> value {address_unit_text!r}")
    elif address_unit_bits != 8:
        warnings.append(
            f"non-byte address unit ({address_unit_bits} bits); debug adapters must scale memory addresses"
        )

    width = _parse_int(_direct_text(root, "width", "32"), 32)
    if width <= 0:
        errors.append("invalid or missing <width>")

    cpu = ""
    cpu_node = _direct(root, "cpu")
    if cpu_node is not None:
        cpu = _direct_text(cpu_node, "name")

    peripherals_node = _direct(root, "peripherals")
    peripherals = _children(peripherals_node, "peripheral") if peripherals_node is not None else []
    if not peripherals:
        errors.append("missing register-bearing <peripherals>")

    peripheral_names: set[str] = set()
    register_count = 0
    field_count = 0
    for peripheral in peripherals:
        peripheral_name = _direct_text(peripheral, "name")
        if peripheral_name in peripheral_names:
            warnings.append(f"duplicate peripheral name {peripheral_name}")
        peripheral_names.add(peripheral_name)

        registers_node = _direct(peripheral, "registers")
        registers = _children(registers_node, "register") if registers_node is not None else []
        register_count += len(registers)
        seen_registers: set[str] = set()
        for register in registers:
            register_name = _direct_text(register, "name")
            if register_name in seen_registers:
                warnings.append(f"{peripheral_name}: duplicate register name {register_name}")
            seen_registers.add(register_name)
            fields_node = _direct(register, "fields")
            fields = _children(fields_node, "field") if fields_node is not None else []
            field_count += len(fields)
            register_size = _parse_int(_direct_text(register, "size"), width)
            for field in fields:
                bit_width = _parse_int(_direct_text(field, "bitWidth"), 0)
                bit_offset = _parse_int(_direct_text(field, "bitOffset"), 0)
                if bit_width > 0 and bit_offset + bit_width > register_size:
                    warnings.append(
                        f"{peripheral_name}.{register_name}: field extends beyond register size"
                    )

    return SvdInfo(
        path=path,
        name=name,
        version=version,
        description=description,
        cpu=cpu,
        address_unit_bits=address_unit_bits,
        width=width,
        peripheral_count=len(peripherals),
        register_count=register_count,
        field_count=field_count,
        warnings=warnings,
        errors=errors,
    )


def current_svds() -> list[SvdInfo]:
    return [inspect_svd(path) for path in iter_svd_files(REPO_ROOT / "svd")]


def build_svd_index(infos: list[SvdInfo]) -> dict[str, list[SvdInfo]]:
    index: dict[str, list[SvdInfo]] = {}
    for info in infos:
        keys = {_normalize_key(info.path.stem), _normalize_key(info.name)}
        for key in keys:
            if key:
                index.setdefault(key, []).append(info)
    return index


def _match_svds(target: str, infos: list[SvdInfo], index: dict[str, list[SvdInfo]]) -> list[SvdInfo]:
    key = _normalize_key(target)
    exact = index.get(key, [])
    if exact:
        return exact
    matches: list[SvdInfo] = []
    target_prefix = target.lower()
    for info in infos:
        stem = info.path.stem.lower()
        if stem.startswith(target_prefix) and len(stem) > len(target_prefix):
            suffix = stem[len(target_prefix):]
            if suffix[0] in {"_", "-", "."}:
                matches.append(info)
    return sorted(matches, key=lambda info: _rel(info.path))


def inventory_targets() -> list[dict[str, str]]:
    svd_infos = current_svds()
    svd_index = build_svd_index(svd_infos)
    records: list[dict[str, str]] = []
    for cfg in sorted((REPO_ROOT / "tcl" / "target").rglob("*.cfg")):
        rel = _rel(cfg)
        stem = cfg.stem
        svds = _match_svds(stem, svd_infos, svd_index)
        vendor = cfg.parent.name if cfg.parent.name != "target" else "generic"
        records.append(
            {
                "target": stem,
                "vendor": vendor,
                "config": rel,
                "svd": ", ".join(_rel(svd.path) for svd in svds),
                "status": "svd-present" if svds else "needs-vendor-svd-source",
            }
        )
    return records


def cmd_list(_: argparse.Namespace) -> int:
    print("SOURCES")
    for source in load_sources():
        print(f"{source['id']:24s} {source['kind']:18s} {source['status']}")
    print("\nCURRENT SVD FILES")
    for info in current_svds():
        state = "OK" if info.ok else "FAIL"
        print(
            f"{state:4s} {_rel(info.path):44s} "
            f"addr={info.address_unit_bits:2d} width={info.width:2d} "
            f"peripherals={info.peripheral_count:3d} registers={info.register_count:4d}"
        )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths] if args.paths else [REPO_ROOT / "svd"]
    svds: list[Path] = []
    for path in paths:
        svds.extend(iter_svd_files(_repo_path(path)))
    status = 0
    for path in svds:
        info = inspect_svd(path)
        state = "OK" if info.ok else "FAIL"
        print(
            f"{state} {_rel(path)}: {info.peripheral_count} peripherals, "
            f"{info.register_count} registers, {info.field_count} fields, "
            f"addressUnitBits={info.address_unit_bits}"
        )
        for warning in info.warnings[: args.max_warnings]:
            print(f"  warning: {warning}")
        hidden = len(info.warnings) - args.max_warnings
        if hidden > 0:
            print(f"  warning: {hidden} additional warnings hidden")
        for error in info.errors:
            print(f"  error: {error}")
        status |= 0 if info.ok else 1
    if not svds:
        print("no SVD files found", file=sys.stderr)
        return 1
    return status


def _write_output(args: argparse.Namespace, text: str) -> None:
    if args.out:
        out = _repo_path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(_rel(out))
    else:
        print(text, end="")


def _markdown_inventory(records: list[dict[str, str]]) -> str:
    lines = [
        "# OpenOCD SVD Inventory",
        "",
        "| Target | Vendor | Target config | SVD | Status |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        svd = ", ".join(f"`{path.strip()}`" for path in record["svd"].split(",") if path.strip())
        lines.append(
            f"| `{record['target']}` | {record['vendor']} | `{record['config']}` | "
            f"{svd} | {record['status']} |"
        )
    return "\n".join(lines) + "\n"


def cmd_inventory(args: argparse.Namespace) -> int:
    records = inventory_targets()
    if args.format == "json":
        text = json.dumps(records, indent=2) + "\n"
    else:
        text = _markdown_inventory(records)
    _write_output(args, text)
    missing = sum(1 for record in records if not record["svd"])
    print(f"inventory: {len(records)} targets, {missing} without local SVD", file=sys.stderr)
    return 0


def _safe_member_name(member: str) -> str:
    name = Path(member.replace("\\", "/")).name
    if not name.lower().endswith(".svd") or name in {"", ".", ".."}:
        raise ValueError(f"unsafe SVD member name: {member}")
    return name


def cmd_import_pack(args: argparse.Namespace) -> int:
    pack = _repo_path(args.pack)
    out_dir = _repo_path(args.out or Path("svd") / args.vendor.lower())
    if not pack.is_file():
        raise FileNotFoundError(pack)
    out_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []
    with zipfile.ZipFile(pack) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".svd")]
        if args.member:
            members = [name for name in members if name == args.member or name.endswith("/" + args.member)]
        if not members:
            raise FileNotFoundError(f"no .svd members found in {pack}")
        for member in members:
            destination = out_dir / _safe_member_name(member)
            if destination.exists() and not args.force:
                print(f"skip existing {_rel(destination)}; pass --force to replace")
                continue
            with archive.open(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            imported.append(destination)
            print(f"imported {_rel(destination)} from {member}")
    failed = 0
    for path in imported:
        info = inspect_svd(path)
        if not info.ok:
            failed = 1
            print(f"FAIL {_rel(path)}", file=sys.stderr)
            for error in info.errors:
                print(f"  error: {error}", file=sys.stderr)
    return failed


def cmd_generate_ti(args: argparse.Namespace) -> int:
    ti_root = REPO_ROOT / "tools" / "ti" / "c2000_toolchain"
    env = os.environ.copy()
    pythonpath = str(ti_root / "src")
    env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "ti_svd.cli", "generate-all"]
    if args.ccs_root:
        command.extend(["--ccs-root", args.ccs_root])
    if args.targetdb:
        command.extend(["--targetdb", args.targetdb])
    if args.skip_fetch:
        command.append("--skip-fetch")
    result = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    if result.returncode:
        return result.returncode

    destination = REPO_ROOT / "svd" / "ti"
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sorted((ti_root / "svd").glob("*.svd")):
        shutil.copy2(source, destination / source.name)
        copied += 1
    print(f"copied {copied} TI SVD files into {_rel(destination)}")
    return cmd_validate(argparse.Namespace(paths=[destination], max_warnings=args.max_warnings))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openocd-svd",
        description="Catalog, validate, import, and generate SVD files for OpenOCD targets",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list SVD sources and committed SVD files")
    p_list.set_defaults(func=cmd_list)

    p_validate = sub.add_parser("validate", help="validate one file, directory, or the whole svd tree")
    p_validate.add_argument("paths", nargs="*")
    p_validate.add_argument("--max-warnings", type=int, default=8)
    p_validate.set_defaults(func=cmd_validate)

    p_inventory = sub.add_parser("inventory", help="inventory OpenOCD target configs and matching SVD files")
    p_inventory.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_inventory.add_argument("--out")
    p_inventory.set_defaults(func=cmd_inventory)

    p_pack = sub.add_parser("import-pack", help="import SVD files from a local CMSIS-Pack archive")
    p_pack.add_argument("--pack", required=True, help="local .pack path")
    p_pack.add_argument("--vendor", required=True, help="output vendor directory under svd/")
    p_pack.add_argument("--out", help="explicit output directory")
    p_pack.add_argument("--member", help="specific archive member or SVD file name")
    p_pack.add_argument("--force", action="store_true")
    p_pack.set_defaults(func=cmd_import_pack)

    p_ti = sub.add_parser("generate-ti", help="run the TI generator and copy output into svd/ti")
    p_ti.add_argument("--ccs-root")
    p_ti.add_argument("--targetdb")
    p_ti.add_argument("--skip-fetch", action="store_true")
    p_ti.add_argument("--max-warnings", type=int, default=8)
    p_ti.set_defaults(func=cmd_generate_ti)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
