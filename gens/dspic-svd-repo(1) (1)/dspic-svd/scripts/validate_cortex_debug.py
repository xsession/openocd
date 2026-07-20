#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd.cortex_debug import validate_cortex_debug_file  # noqa: E402


def candidates(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_dir():
            result.extend(sorted(path.glob("*.svd")))
        else:
            result.append(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the exact CMSIS-SVD subset consumed by Cortex-Debug"
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    files = candidates(args.paths)
    if not files:
        print("no SVD files found", file=sys.stderr)
        return 1
    for path in files:
        errors = validate_cortex_debug_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}", file=sys.stderr)
        else:
            print(f"Cortex-Debug compatible: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
