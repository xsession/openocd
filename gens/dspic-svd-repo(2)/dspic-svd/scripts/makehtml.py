#!/usr/bin/env python3
from __future__ import annotations

import html
from xml.etree import ElementTree as ET

from common import ROOT


def child_text(node: ET.Element, tag: str, default: str = "") -> str:
    return next((c.text or default for c in node if c.tag.rsplit("}", 1)[-1] == tag), default)


def render(svd):
    root = ET.parse(svd).getroot()
    name = child_text(root, "name", svd.stem)
    rows = []
    for register in (n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "register"):
        fields = []
        for field in (n for n in register.iter() if n.tag.rsplit("}", 1)[-1] == "field"):
            fields.append(
                f"{child_text(field, 'name')}[{child_text(field, 'bitOffset')}+:{child_text(field, 'bitWidth')}]"
            )
        rows.append(
            (
                int(child_text(register, "addressOffset", "0"), 0),
                child_text(register, "name"),
                child_text(register, "access"),
                child_text(register, "description"),
                ", ".join(fields),
            )
        )
    body = "\n".join(
        f"<tr><td><code>0x{addr:04X}</code></td><td><code>{html.escape(reg)}</code></td><td>{html.escape(access)}</td><td>{html.escape(desc)}</td><td><code>{html.escape(fields)}</code></td></tr>"
        for addr, reg, access, desc, fields in sorted(rows)
    )
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(name)} registers</title><style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:.4rem;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#eee}}code{{white-space:nowrap}}</style></head><body><h1>{html.escape(name)} register map</h1><p>{len(rows)} registers</p><table><thead><tr><th>Address</th><th>Register</th><th>Access</th><th>Description</th><th>Fields</th></tr></thead><tbody>{body}</tbody></table></body></html>"""


def main() -> int:
    out = ROOT / "html"
    out.mkdir(exist_ok=True)
    links = []
    for svd in sorted((ROOT / "svd").glob("*.svd")):
        target = out / f"{svd.stem}.html"
        target.write_text(render(svd), encoding="utf-8")
        links.append(f"<li><a href='{target.name}'>{svd.stem}</a></li>")
    (out / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><h1>dsPIC SVD register maps</h1><ul>"
        + "".join(links)
        + "</ul>",
        encoding="utf-8",
    )
    print(out / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
