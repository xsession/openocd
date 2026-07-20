from __future__ import annotations

import argparse
from pathlib import Path

from .convert import convert_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Microchip ATDF/EDC XML to CMSIS-SVD")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--device-name")
    args = parser.parse_args()
    device = convert_file(args.source, args.output, args.device_name)
    print(f"generated {args.output}: {len(device.registers)} registers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
