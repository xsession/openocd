#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import ZipFile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"release validation failed: {message}")


def main() -> int:
    archive_path = Path(sys.argv[1])
    require(archive_path.is_file(), str(archive_path))
    version = archive_path.stem.removeprefix("ti-c2000-toolchain-")
    prefix = f"ti-c2000-toolchain-{version}/"
    with ZipFile(archive_path) as archive:
        bad = archive.testzip()
        require(bad is None, f"corrupt member: {bad}")
        names = set(archive.namelist())
        required = {
            prefix + "VERSION",
            prefix + "README.md",
            prefix + "pyproject.toml",
            prefix + "extension/package.json",
            prefix + f"extension/c2000-debug-{version}.vsix",
            prefix + "openocd/scripts/apply_xds100_support.py",
            prefix + "openocd/overlay/tcl/interface/ftdi/xds100v2.cfg",
            prefix + "openocd/overlay/tcl/interface/ftdi/xds100v3.cfg",
            prefix + "src/ti_svd/cli.py",
            prefix + "bridge/ccs-debug-bridge.js",
            prefix + "extension/src/backends/renodeBackend.ts",
            prefix + "extension/src/backends/openocdBackend.ts",
        }
        missing = sorted(required - names)
        require(not missing, f"missing members: {missing}")
        package = json.loads(archive.read(prefix + "extension/package.json"))
        require(package["version"] == version, "extension version mismatch")
        stale = [name for name in names if "c2000-debug-0.1.0.vsix" in name or "c2000-debug-0.2.0.vsix" in name]
        require(not stale, f"stale VSIX files: {stale}")
    print(f"Release validation passed: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
