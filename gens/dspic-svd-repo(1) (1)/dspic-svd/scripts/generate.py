#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tomllib

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))
from dspic_svd.convert import convert_file  # noqa: E402


def devices() -> list[str]:
    with (ROOT / "packs.toml").open("rb") as handle:
        manifest = tomllib.load(handle)
    return [device for pack in manifest["packs"] for device in pack["devices"]]


def generate(device: str) -> None:
    sources = list((ROOT / "sources").glob(f"{device}.*"))
    sources = [p for p in sources if p.suffix.lower() in {".pic", ".atdf"}]
    if not sources:
        raise SystemExit(f"source for {device} not found; run make update first")
    output = ROOT / "svd" / f"{device.lower()}.svd"
    model = convert_file(sources[0], output, device)
    print(f"generated {output.relative_to(ROOT)} ({len(model.registers)} registers)")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--device")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    targets = devices() if args.all else [args.device]
    by_lower = {d.lower(): d for d in devices()}
    for target in targets:
        canonical = by_lower.get(target.lower(), target)
        generate(canonical)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
