from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ccs import find_device_xml, find_targetdb_roots
from .cmsis import build_svd, write_svd
from .config import list_manifests, load_manifest, repository_root
from .pack import generate_mspm0
from .patch import apply_patch
from .tixml import parse_device
from .validate import validate_svd


def _targetdb_from_args(args: argparse.Namespace) -> Path:
    if getattr(args, "targetdb", None):
        path = Path(args.targetdb).expanduser().resolve()
        if not (path / "devices").is_dir() or not (path / "Modules").is_dir():
            raise FileNotFoundError(f"not a CCS targetdb root: {path}")
        return path
    ccs_root = getattr(args, "ccs_root", None)
    roots = find_targetdb_roots(Path(ccs_root).expanduser() if ccs_root else None)
    if not roots:
        raise FileNotFoundError("no CCS targetdb found; pass --ccs-root or --targetdb")
    return roots[0]


def _validate_generated(device_id: str, output: Path) -> int:
    manifest = load_manifest(device_id)
    result = validate_svd(
        output,
        require_cortex_debug=manifest.cortex_debug,
        expected_core=manifest.core if manifest.cortex_debug else None,
    )
    profile = "Cortex-Debug" if manifest.cortex_debug else "SVD viewer"
    print(
        f"validation ({profile}): {result.peripheral_count} peripherals, "
        f"{result.register_count} registers, {result.field_count} fields"
    )
    for warning in result.warnings[:20]:
        print(f"warning: {warning}", file=sys.stderr)
    if not result.ok:
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    for device_id in list_manifests():
        manifest = load_manifest(device_id)
        mode = "cortex-debug" if manifest.cortex_debug else "c2000-debug"
        print(f"{device_id:24s} {manifest.core:8s} {mode}")
    return 0


def cmd_compatibility(_: argparse.Namespace) -> int:
    print("DEVICE                   CORE      DEBUG ADAPTER  INTENDED USE")
    for device_id in list_manifests():
        manifest = load_manifest(device_id)
        adapter = "cortex-debug" if manifest.cortex_debug else "c2000-debug"
        use = "debug + peripherals"
        print(f"{device_id:24s} {manifest.core:8s} {adapter:14s} {use}")
        if manifest.compatibility_note:
            print(f"  {manifest.compatibility_note}")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    targetdb = _targetdb_from_args(args)
    print(f"targetdb: {targetdb}")
    devices = [args.device] if args.device else [
        device_id for device_id in list_manifests()
        if load_manifest(device_id).source == "ccs-targetdb"
    ]
    for device_id in devices:
        manifest = load_manifest(device_id)
        print(f"\n[{device_id}]")
        matches = find_device_xml(targetdb, manifest)
        if not matches:
            print("  no matching device XML")
        for index, match in enumerate(matches[:20], 1):
            print(f"  {index:2d}. {match}")
    return 0


def _generate_ccs(device_id: str, args: argparse.Namespace) -> Path:
    root = repository_root()
    manifest = load_manifest(device_id, root)
    targetdb = _targetdb_from_args(args)
    device_xml_arg = getattr(args, "device_xml", None)
    if device_xml_arg:
        device_xml = Path(device_xml_arg).expanduser().resolve()
    else:
        matches = find_device_xml(targetdb, manifest)
        if not matches:
            raise FileNotFoundError(f"no CCS device XML found for {device_id}")
        device_xml = matches[0]
    peripherals = parse_device(device_xml, targetdb, manifest)
    if not peripherals:
        raise RuntimeError(f"no register-bearing peripherals parsed from {device_xml}")
    svd = build_svd(manifest, peripherals, f"TI CCS targetdb file {device_xml.name}")
    write_svd(svd, manifest.output)
    apply_patch(manifest.output, root / "patches" / f"{device_id}.json")
    print(f"generated {manifest.output} from {device_xml} ({len(peripherals)} peripherals)")
    return manifest.output


def cmd_generate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.device)
    if manifest.source == "cmsis-pack":
        output = generate_mspm0(
            manifest,
            offline_pack=Path(args.pack).expanduser() if args.pack else None,
        )
        print(f"generated {output}")
    else:
        output = _generate_ccs(args.device, args)
    return _validate_generated(args.device, output)


def cmd_generate_all(args: argparse.Namespace) -> int:
    failed: list[str] = []
    for device_id in list_manifests():
        manifest = load_manifest(device_id)
        try:
            if manifest.source == "cmsis-pack":
                if args.skip_fetch:
                    print(f"skip {device_id}: --skip-fetch")
                    continue
                output = generate_mspm0(manifest)
                print(f"generated {output}")
            else:
                output = _generate_ccs(device_id, args)
            if _validate_generated(device_id, output):
                failed.append(device_id)
        except Exception as exc:  # continue to report every device
            failed.append(device_id)
            print(f"failed {device_id}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _manifest_for_path(path: Path):
    resolved = path.resolve()
    for device_id in list_manifests():
        manifest = load_manifest(device_id)
        if manifest.output.resolve() == resolved:
            return manifest
    return None


def cmd_validate(args: argparse.Namespace) -> int:
    paths = [Path(path) for path in args.paths] if args.paths else sorted(
        (repository_root() / "svd").glob("*.svd")
    )
    status = 0
    for path in paths:
        manifest = _manifest_for_path(path)
        require_cortex_debug = bool(args.cortex_debug) or bool(manifest and manifest.cortex_debug)
        expected_core = manifest.core if manifest and require_cortex_debug else None
        result = validate_svd(
            path,
            require_cortex_debug=require_cortex_debug,
            expected_core=expected_core,
        )
        state = "OK" if result.ok else "FAIL"
        profile = "cortex-debug" if require_cortex_debug else "svd-viewer"
        print(
            f"{state} [{profile}] {path}: {result.peripheral_count} peripherals, "
            f"{result.register_count} registers, {result.field_count} fields"
        )
        for warning in result.warnings:
            print(f"  warning: {warning}")
        for error in result.errors:
            print(f"  error: {error}")
        status |= 0 if result.ok else 1
    return status


def _default_svd_reference(manifest) -> str:
    return f"${{workspaceFolder}}/svd/{manifest.output.name}"


def cmd_vscode_config(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.device)
    svd_key = "svdFile" if args.legacy_svd_file else "svdPath"
    svd_reference = args.svd_path or _default_svd_reference(manifest)

    if args.peripheral_viewer_only:
        config: dict[str, object] = {svd_key: svd_reference}
    elif manifest.cortex_debug and args.adapter in {"auto", "cortex-debug"}:
        config = {
            "name": args.name or f"{manifest.name} ({args.servertype})",
            "type": "cortex-debug",
            "request": args.request,
            "servertype": args.servertype,
            "cwd": "${workspaceFolder}",
            "executable": args.executable,
            "device": manifest.name,
            svd_key: svd_reference,
            "runToEntryPoint": args.run_to_entry,
            "showDevDebugOutput": "none",
        }
        if args.config_file:
            config["configFiles"] = args.config_file
        if args.servertype == "external":
            if not args.gdb_target:
                raise RuntimeError("--gdb-target is required with --servertype external")
            config["gdbTarget"] = args.gdb_target
        if args.serverpath:
            config["serverpath"] = args.serverpath
        if args.gdb_path:
            config["gdbPath"] = args.gdb_path
    else:
        backend = args.backend
        config = {
            "name": args.name or f"{manifest.name} ({backend})",
            "type": "c2000-debug",
            "request": args.request,
            "backend": backend,
            "cwd": "${workspaceFolder}",
            "device": manifest.id,
            "executable": args.executable,
            "svdPath": svd_reference,
            "addressScale": args.address_scale or manifest.address_scale,
            "registerProfile": args.register_profile,
            "runToEntryPoint": args.run_to_entry,
        }
        if args.ccs_root:
            config["ccsRoot"] = args.ccs_root
        elif backend == "ccs":
            config["ccsRoot"] = "C:/ti/ccs2040"
        if args.ccxml:
            config["ccxml"] = args.ccxml
        elif backend == "ccs":
            config["ccxml"] = f"${{workspaceFolder}}/targetConfigs/{manifest.id}.ccxml"
        if args.core_pattern:
            config["corePattern"] = args.core_pattern
        elif manifest.core.upper().startswith("C28"):
            config["corePattern"] = "C28xx|C28x"
        if backend == "openocd":
            config["openocdHost"] = args.openocd_host
            config["openocdTelnetPort"] = args.openocd_telnet_port

    text = json.dumps(config, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        print(destination)
    else:
        print(text, end="")
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ti-svd",
        description="Generate TI SVD files and VS Code debug configuration fragments",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list supported device manifests and compatibility")
    p_list.set_defaults(func=cmd_list)

    p_compat = sub.add_parser("compatibility", help="show the VS Code debug-adapter compatibility matrix")
    p_compat.set_defaults(func=cmd_compatibility)

    p_discover = sub.add_parser("discover", help="find matching C2000 device XML files in CCS")
    p_discover.add_argument("--device", choices=list_manifests())
    p_discover.add_argument("--ccs-root")
    p_discover.add_argument("--targetdb")
    p_discover.set_defaults(func=cmd_discover)

    p_generate = sub.add_parser("generate", help="generate one SVD")
    p_generate.add_argument("device", choices=list_manifests())
    p_generate.add_argument("--ccs-root")
    p_generate.add_argument("--targetdb")
    p_generate.add_argument("--device-xml")
    p_generate.add_argument("--pack", help="offline CMSIS .pack path")
    p_generate.set_defaults(func=cmd_generate)

    p_all = sub.add_parser("generate-all", help="generate every SVD")
    p_all.add_argument("--ccs-root")
    p_all.add_argument("--targetdb")
    p_all.add_argument("--device-xml")
    p_all.add_argument("--skip-fetch", action="store_true")
    p_all.set_defaults(func=cmd_generate_all)

    p_validate = sub.add_parser("validate", help="validate generated SVD files")
    p_validate.add_argument("paths", nargs="*")
    p_validate.add_argument(
        "--cortex-debug",
        action="store_true",
        help="require a byte-addressed Cortex-M CPU profile for every supplied SVD",
    )
    p_validate.set_defaults(func=cmd_validate)

    p_vscode = sub.add_parser("vscode-config", help="emit a Cortex-Debug or C2000 Debug launch config")
    p_vscode.add_argument("device", choices=list_manifests())
    p_vscode.add_argument("--name")
    p_vscode.add_argument("--request", choices=["launch", "attach"], default="launch")
    p_vscode.add_argument(
        "--servertype",
        choices=["openocd", "jlink", "pyocd", "external", "bmp", "qemu"],
        default="openocd",
    )
    p_vscode.add_argument("--executable", default="${workspaceFolder}/build/app.elf")
    p_vscode.add_argument("--svd-path")
    p_vscode.add_argument("--run-to-entry", default="main")
    p_vscode.add_argument("--config-file", action="append", default=[])
    p_vscode.add_argument("--gdb-target")
    p_vscode.add_argument("--serverpath")
    p_vscode.add_argument("--gdb-path")
    p_vscode.add_argument("--output")
    p_vscode.add_argument(
        "--legacy-svd-file",
        action="store_true",
        help="use the older svdFile key instead of current svdPath",
    )
    p_vscode.add_argument(
        "--peripheral-viewer-only",
        action="store_true",
        help="for non-Cortex C28x targets, emit only the SVD viewer properties",
    )
    p_vscode.add_argument(
        "--adapter",
        choices=["auto", "cortex-debug", "c2000-debug"],
        default="auto",
        help="debug adapter to generate; auto uses Cortex-Debug for Arm and c2000-debug for C28x",
    )
    p_vscode.add_argument("--backend", choices=["ccs", "openocd", "mock"], default="ccs")
    p_vscode.add_argument("--ccs-root")
    p_vscode.add_argument("--ccxml")
    p_vscode.add_argument("--core-pattern")
    p_vscode.add_argument("--address-scale", type=int, choices=[1, 2])
    p_vscode.add_argument(
        "--register-profile",
        choices=["auto", "c28x", "c28x-fpu-vcu", "c28x-fpu-tmu-vcu", "cortex-m3"],
        default="auto",
    )
    p_vscode.add_argument("--openocd-host", default="127.0.0.1")
    p_vscode.add_argument("--openocd-telnet-port", type=int, default=4444)
    p_vscode.set_defaults(func=cmd_vscode_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
