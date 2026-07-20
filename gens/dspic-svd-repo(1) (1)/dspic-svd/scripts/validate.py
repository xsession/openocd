#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd.validate import validate_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "svd")
    args = parser.parse_args()
    paths = sorted(args.path.glob("*.svd")) if args.path.is_dir() else [args.path]
    if not paths:
        print("no generated SVD files; structural validation skipped")
        return 0
    failed = False
    for path in paths:
        errors = validate_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}", file=sys.stderr)
        else:
            print(f"OK {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
