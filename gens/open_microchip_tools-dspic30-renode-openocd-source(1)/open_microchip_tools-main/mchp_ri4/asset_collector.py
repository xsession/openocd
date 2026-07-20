from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from .repo_assets import collect_repo_assets, collect_supported_family_packs, vendor_root


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Collect required MPLAB pack assets into the repository")
    parser.add_argument("--mplab-root", default=r"C:\Program Files\Microchip\MPLABX\v6.30")
    parser.add_argument("--tool", choices=("pk4", "icd4"), default="pk4")
    parser.add_argument("--all-supported", action="store_true", help="Collect all family packs supported by PK4 and ICD4")
    parser.add_argument("--tools", nargs="+", default=("pk4", "icd4"), help="Tools to consider with --all-supported")
    parser.add_argument("--processor", default="")
    parser.add_argument("--output-root", default=str(vendor_root()))
    args = parser.parse_args(list(argv) if argv is not None else None)

    if bool(args.all_supported):
        result = collect_supported_family_packs(
            mplab_root=Path(str(args.mplab_root)),
            tools=tuple(str(tool) for tool in args.tools),
            destination_root=Path(str(args.output_root)),
        )
    else:
        result = collect_repo_assets(
            mplab_root=Path(str(args.mplab_root)),
            tool=str(args.tool),
            processor=str(args.processor).strip() or None,
            destination_root=Path(str(args.output_root)),
        ).to_dict()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())