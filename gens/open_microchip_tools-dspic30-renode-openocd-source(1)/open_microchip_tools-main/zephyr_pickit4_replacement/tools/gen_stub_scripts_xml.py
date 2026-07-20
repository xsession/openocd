from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

from mchp_ri4.family_profiles import get_family_profile


STUB_OPCODES: Dict[str, int] = {
    "EnterDebugMode": 0x10,
    "EnterDebugModeHvSp": 0x10,
    "EnterDebugModeHvSpRst": 0x10,
    "EnterDebugModeHvUpt": 0x10,
    "GetPC": 0x11,
    "SetPC": 0x12,
    "Run": 0x13,
    "Halt": 0x14,
    "SingleStep": 0x15,
    "SingleStepUFEX": 0x16,
    "EraseChip": 0x20,
    "EraseProgmemRange": 0x20,
    "EraseDataEEmemRange": 0x20,
    "EraseDataEEmem": 0x20,
    "EraseTestmemRange": 0x20,
    "EraseOcdProgmemPreOne": 0x20,
    "EraseOcdProgmemPreTwo": 0x20,
    "WriteProgmem": 0x21,
    "WriteProgmemPE": 0x21,
    "P32PE_ProgramCluster": 0x21,
    "WriteProgmemDE": 0x21,
    "WriteConfigmem": 0x21,
    "WriteConfigmemDE": 0x21,
    "WriteOtpConfigmem": 0x21,
    "WriteTestmem": 0x21,
    "WriteRAM": 0x21,
    "WriteBootMem": 0x21,
    "WriteOcdProgmem": 0x21,
    "ReadProgmem": 0x22,
    "ReadProgmemPE": 0x22,
    "ReadRAM": 0x22,
    "ReadProgmemDE": 0x22,
    "ReadTestmem": 0x22,
    "ReadOcdProgmem": 0x22,
    "ReadConfigmem": 0x22,
    "ReadConfigmemFuse": 0x22,
    "ReadConfigmemLock": 0x22,
    "EnterTMOD_LV": 0x30,
    "EnterTMOD_HV": 0x30,
    "EnterTMOD_PE": 0x30,
    "EnterProgMode": 0x30,
    "EnterProgModeHvSp": 0x30,
    "EnterProgModeHvSpRst": 0x30,
    "EnterProgModeHvUpt": 0x30,
    "InitJTAG": 0x30,
    "SetupSerialMode": 0x30,
    "LoadLoader": 0x30,
    "DownloadPE": 0x30,
    "TestPEConnect": 0x30,
    "ExitTMOD": 0x31,
    "ExitProgMode": 0x31,
}

NOOP_OPCODE = 0x7F
MAGIC0 = 0x5A
MAGIC1 = 0xA5


def build_family_stub_scripts(family: str) -> List[Dict[str, object]]:
    profile = get_family_profile(family)
    ordered: List[str] = []
    seen = set()
    for names in (
        profile.program_entry_scripts,
        profile.program_exit_scripts,
        profile.erase_scripts,
        profile.write_program_scripts,
        profile.read_program_scripts,
        profile.write_config_scripts,
        profile.read_config_scripts,
        profile.enter_debug_scripts,
        profile.get_pc_scripts,
        profile.set_pc_scripts,
        profile.run_scripts,
        profile.step_scripts,
        profile.halt_scripts,
    ):
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            ordered.append(name)

    result: List[Dict[str, object]] = []
    for name in ordered:
        opcode = STUB_OPCODES.get(name, NOOP_OPCODE)
        result.append({"name": name, "bytes": [MAGIC0, MAGIC1, opcode]})
    return result


def render_scripts_xml(processor: str, scripts: Iterable[Dict[str, object]]) -> str:
    lines = [
        "<devicefile>",
        f"  <processor>{processor}</processor>",
    ]
    for item in scripts:
        lines.append("  <script>")
        lines.append(f"    <function>{item['name']}</function>")
        lines.append("    <scrbytes>")
        for byte in item["bytes"]:
            lines.append(f"      <byte>0x{int(byte):02X}</byte>")
        lines.append("    </scrbytes>")
        lines.append("  </script>")
    lines.append("</devicefile>")
    lines.append("")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Zephyr stub scripts.xml for a modeled RI4 family")
    parser.add_argument("--family", required=True)
    parser.add_argument("--processor", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    xml_text = render_scripts_xml(args.processor, build_family_stub_scripts(args.family))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())