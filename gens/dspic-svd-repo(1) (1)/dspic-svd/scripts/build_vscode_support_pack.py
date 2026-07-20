#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd import __version__  # noqa: E402
from dspic_svd.cortex_debug import validate_cortex_debug_file  # noqa: E402

DEVICES = (
    "dspic30f5011",
    "dspic33fj128mc802",
    "dspic33fj128mc804",
    "dspic33ep128gm604",
)


def prepare() -> Path:
    extension_dir = ROOT / "vscode-support"
    data_dir = extension_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    for device in DEVICES:
        source = ROOT / "svd" / f"{device}.svd"
        if not source.exists():
            raise SystemExit(f"missing {source.relative_to(ROOT)}; run make update first")
        errors = validate_cortex_debug_file(source)
        if errors:
            joined = "\n".join(f"  - {error}" for error in errors)
            raise SystemExit(
                f"{source.relative_to(ROOT)} is not Cortex-Debug compatible:\n{joined}"
            )
        shutil.copy2(source, data_dir / source.name)

    package_path = extension_dir / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["version"] = __version__
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    print(f"prepared {extension_dir.relative_to(ROOT)} with {len(DEVICES)} SVD files")
    return extension_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or package the Cortex-Debug support pack")
    parser.add_argument("--package", action="store_true", help="also build a VSIX with npx vsce")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "cortex-debug-dp-dspic.vsix")
    args = parser.parse_args()

    extension_dir = prepare()
    if args.package:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "npx",
                "--yes",
                "@vscode/vsce",
                "package",
                "--out",
                str(args.out.resolve()),
            ],
            cwd=extension_dir,
            check=True,
        )
        print(
            f"created {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
