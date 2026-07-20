#!/usr/bin/env python3
"""Inspect xsession/renode custom-cores for C2000 debugger compatibility."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_REGISTERS = [
    "ACC", "AH", "AL", "P", "PH", "PL", "XT", "T",
    *[f"XAR{i}" for i in range(8)],
    *[f"AR{i}" for i in range(8)],
    "SP", "PC", "RPC", "ST0", "ST1", "IFR", "IER", "DP",
]


def find(root: Path, suffix: str) -> Path | None:
    matches = list(root.rglob(suffix))
    return matches[0] if matches else None


def inspect(renode_root: Path, infrastructure_root: Path, renode_commit: str | None = None, infrastructure_commit: str | None = None) -> dict[str, object]:
    reg_file = find(infrastructure_root, "C2000Registers.cs")
    cpu_file = find(infrastructure_root, "C2000.cs")
    f28069 = find(renode_root, "tms320f28069.repl")
    f280049 = find(renode_root, "tms320f280049c.repl")
    f28m35 = list(renode_root.rglob("*28m35*.repl"))
    smoke_repl = find(renode_root, "c2000_blink.repl")
    smoke_log = find(renode_root, "test_c2000.log")

    registers: list[str] = []
    if reg_file:
        text = reg_file.read_text(encoding="utf-8", errors="replace")
        indexed = re.findall(r"C2000Registers\.([A-Z0-9]+),\s+new CPURegister\(\s*(\d+)", text)
        registers = [name for name, _ in sorted(indexed, key=lambda item: int(item[1]))]

    gdb_features_empty = None
    architecture = None
    if cpu_file:
        text = cpu_file.read_text(encoding="utf-8", errors="replace")
        architecture_match = re.search(r'GDBArchitecture\s*=>\s*"([^"]+)"', text)
        architecture = architecture_match.group(1) if architecture_match else None
        gdb_features_empty = bool(re.search(r"GDBFeatures\s*=>\s*\n?\s*new List<GDBFeatureDescriptor>\(\)", text))

    log_text = smoke_log.read_text(encoding="utf-8", errors="replace") if smoke_log else ""
    repl_text = smoke_repl.read_text(encoding="utf-8", errors="replace") if smoke_repl else ""
    result = {
        "source": {"renode_commit": renode_commit, "infrastructure_commit": infrastructure_commit},
        "c2000_cpu_present": bool(cpu_file),
        "gdb_architecture": architecture,
        "gdb_features_empty": gdb_features_empty,
        "register_mapping": registers,
        "register_mapping_matches_adapter": registers == EXPECTED_REGISTERS,
        "platforms": {
            "tms320f28069": bool(f28069),
            "tms320f280049": bool(f280049),
            "tms320f28m35x": bool(f28m35),
        },
        "branch_smoke_test": {
            "completed_marker": ">>> c2000: completed <<<" in log_text,
            "core_dump_after_completion": "dumped core" in log_text.lower(),
            "store_instruction_not_implemented_note": "No memory store instruction implemented yet" in repl_text,
        },
        "recommended_backend": "renode-monitor" if gdb_features_empty else "gdb-or-renode-monitor",
    }
    result["compatible_for_monitor_adapter_tests"] = bool(
        result["c2000_cpu_present"]
        and result["register_mapping_matches_adapter"]
        and result["platforms"]["tms320f28069"]
        and result["platforms"]["tms320f280049"]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renode-root", type=Path, required=True)
    parser.add_argument("--infrastructure-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--renode-commit")
    parser.add_argument("--infrastructure-commit")
    args = parser.parse_args()
    result = inspect(args.renode_root, args.infrastructure_root, args.renode_commit, args.infrastructure_commit)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["compatible_for_monitor_adapter_tests"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
