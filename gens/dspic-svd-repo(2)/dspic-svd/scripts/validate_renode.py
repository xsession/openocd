#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dspic_svd.renode import diagnostics_exit_code, validate_renode_tree


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate xsession/renode custom-cores dsPIC integration")
    parser.add_argument("--renode-root", required=True, type=Path, help="Path to a custom-cores Renode checkout")
    parser.add_argument("--svd-dir", type=Path, default=Path("svd"), help="Generated SVD directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as a non-zero result")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write a machine-readable report")
    args = parser.parse_args()

    diagnostics = validate_renode_tree(args.renode_root.resolve(), args.svd_dir.resolve())
    for diagnostic in diagnostics:
        location = f" [{diagnostic.path}]" if diagnostic.path else ""
        print(f"{diagnostic.severity.upper():7} {diagnostic.code}: {diagnostic.message}{location}")

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(
                {
                    "renode_root": str(args.renode_root.resolve()),
                    "svd_dir": str(args.svd_dir.resolve()),
                    "diagnostics": [item.to_dict() for item in diagnostics],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return diagnostics_exit_code(diagnostics, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
