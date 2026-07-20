#!/usr/bin/env python3
from __future__ import annotations

from xml.etree import ElementTree as ET

from common import ROOT


def child_text(node: ET.Element, tag: str, default: str = "") -> str:
    return next((c.text or default for c in node if c.tag.rsplit("}", 1)[-1] == tag), default)


def main() -> int:
    out_dir = ROOT / "mmaps"
    out_dir.mkdir(exist_ok=True)
    for svd in sorted((ROOT / "svd").glob("*.svd")):
        root = ET.parse(svd).getroot()
        rows = []
        for register in (n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "register"):
            rows.append(
                (
                    int(child_text(register, "addressOffset", "0"), 0),
                    child_text(register, "name"),
                    child_text(register, "description"),
                )
            )
        target = out_dir / f"{svd.stem}.mmap"
        target.write_text(
            "\n".join(f"0x{addr:04X} {name:<32} {desc}" for addr, name, desc in sorted(rows))
            + "\n",
            encoding="utf-8",
        )
        print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
