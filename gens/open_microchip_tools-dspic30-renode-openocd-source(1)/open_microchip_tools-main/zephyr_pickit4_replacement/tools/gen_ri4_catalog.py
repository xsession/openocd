from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

from mchp_ri4.family_profiles import family_inventory


def build_catalog_entries() -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for item in family_inventory():
        scripts = sorted(
            {
                *(str(name) for name in item.get("programmerScripts", [])),
                *(str(name) for name in item.get("debuggerScripts", [])),
                *(str(name) for name in item.get("programEntryScripts", [])),
                *(str(name) for name in item.get("programExitScripts", [])),
                *(str(name) for name in item.get("eraseScripts", [])),
                *(str(name) for name in item.get("writeProgramScripts", [])),
                *(str(name) for name in item.get("readProgramScripts", [])),
                *(str(name) for name in item.get("enterDebugScripts", [])),
                *(str(name) for name in item.get("getPcScripts", [])),
                *(str(name) for name in item.get("setPcScripts", [])),
                *(str(name) for name in item.get("runScripts", [])),
                *(str(name) for name in item.get("stepScripts", [])),
                *(str(name) for name in item.get("haltScripts", [])),
            }
        )
        entries.append(
            {
                "family": str(item["family"]),
                "behavior": str(item.get("behavior") or "unknown-behavior"),
                "supportsProgramming": bool(item.get("supportsProgramming", False)),
                "supportsDebugging": bool(item.get("supportsDebugging", False)),
                "supportsSetPc": bool(item.get("supportsSetPc", False)),
                "scripts": scripts,
            }
        )
    return entries


def _c_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def render_header(entries: Iterable[Dict[str, object]]) -> str:
    items = list(entries)
    lines: List[str] = [
        "#ifndef ZEPHYR_PICKIT4_REPLACEMENT_RI4_FAMILY_CATALOG_DATA_H_",
        "#define ZEPHYR_PICKIT4_REPLACEMENT_RI4_FAMILY_CATALOG_DATA_H_",
        "",
    ]

    for index, entry in enumerate(items):
        scripts = entry["scripts"]
        lines.append(f"static const char * const ri4_family_scripts_{index}[] = {{")
        for script in scripts:
            lines.append(f'    "{_c_string(str(script))}",')
        lines.append("};")
        lines.append("")

    lines.append("static const struct ri4_family_catalog_entry ri4_family_catalog[] = {")
    for index, entry in enumerate(items):
        lines.append("    {")
        lines.append(f'        .family = "{_c_string(str(entry["family"]))}",')
        lines.append(f'        .behavior = "{_c_string(str(entry["behavior"]))}",')
        lines.append(f'        .supports_programming = {str(bool(entry["supportsProgramming"])).lower()},')
        lines.append(f'        .supports_debugging = {str(bool(entry["supportsDebugging"])).lower()},')
        lines.append(f'        .supports_set_pc = {str(bool(entry["supportsSetPc"])).lower()},')
        lines.append(f"        .scripts = ri4_family_scripts_{index},")
        lines.append(f"        .script_count = {len(entry['scripts'])}U,")
        lines.append("    },")
    lines.append("};")
    lines.append("")
    lines.append("static const size_t ri4_family_catalog_count = sizeof(ri4_family_catalog) / sizeof(ri4_family_catalog[0]);")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Zephyr-friendly RI4 family catalog from the repo Python model")
    parser.add_argument("--format", choices=["header"], default="header")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    entries = build_catalog_entries()
    rendered = render_header(entries)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())