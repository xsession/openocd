from __future__ import annotations

import argparse
import json
from typing import List

from .pic18_stub_session import SUPPORTED_STUB_FAMILIES, create_stub_family_session, generate_stub_family_xml_file
from .pk4_observed_session import create_pk4_observed_session


def run_stub_demo(
    *,
    family: str = "PIC18",
    processor: str = "PIC18F_STUB",
    write_address: int = 0x10,
    write_data: bytes = b"\x01\x02\x03\x04",
) -> dict:
    session, probe = create_stub_family_session(family, processor)
    scripts_path = generate_stub_family_xml_file(family, processor)

    try:
        session.enter_debug_mode()
        if session.profile is not None and session.profile.set_pc_scripts:
            session.set_pc(0x12345678)
        pc = session.get_pc()
        if session.profile is not None and session.profile.erase_scripts:
            session.erase_chip()
        session.write_program(write_address, write_data)
        read_back = session.read_program(write_address, len(write_data))
        return {
            "family": family.strip().upper(),
            "scriptsPath": str(scripts_path),
            "inventory": session.script_inventory(),
            "pc": pc,
            "readBack": read_back,
            "status": {
                "Commands in progress": probe.get_status_value("Commands in progress"),
                "Debug Mode": probe.get_status_value("Debug Mode"),
                "Target Halted": probe.get_status_value("Target Halted"),
                "Program Counter": probe.get_status_value("Program Counter"),
                "Family": probe.get_status_value("Family"),
            },
        }
    finally:
        session.close()
        scripts_path.unlink(missing_ok=True)


def run_pk4_observed_demo() -> dict:
    session, probe = create_pk4_observed_session()

    try:
        session.enter_debug_mode()
        session.write_primary_slot(0x20, b"APP!")
        session.write_secondary_slot(0x10, b"DAP!")
        primary_read = session.read_primary_slot(0x20, 4)
        secondary_read = session.read_secondary_slot(0x10, 4)

        return {
            "family": "ARM_MPU",
            "inventory": session.script_inventory(),
            "primaryReadBack": primary_read,
            "secondaryReadBack": secondary_read,
            "status": {
                "Probe Profile": session.get_status_value("Probe Profile"),
                "Primary Role": session.get_status_value("Primary Role"),
                "Secondary Role": session.get_status_value("Secondary Role"),
                "Secondary Identity": session.get_status_value("Secondary Identity"),
                "Execution Slot": session.get_status_value("Execution Slot"),
                "Last Program Region": session.get_status_value("Last Program Region"),
                "Last Program Role": session.get_status_value("Last Program Role"),
            },
            "probeStatus": {
                "Execution Slot": probe.get_status_value("Execution Slot"),
                "Last Program Region": probe.get_status_value("Last Program Region"),
                "Last Program Role": probe.get_status_value("Last Program Role"),
            },
        }
    finally:
        session.close()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a repo-local Zephyr stub session demo")
    parser.add_argument("--mode", choices=("stub", "pk4-observed"), default="stub")
    parser.add_argument("--family", choices=list(SUPPORTED_STUB_FAMILIES), default="PIC18")
    parser.add_argument("--processor", default="")
    parser.add_argument("--write-address", default="0x10")
    parser.add_argument("--write-hex", default="01020304")
    args = parser.parse_args(argv)

    if args.mode == "pk4-observed":
        print(json.dumps(run_pk4_observed_demo(), indent=2, sort_keys=True))
        return 0

    family = str(args.family).strip().upper()
    default_processors = {
        "PIC18": "PIC18F_STUB",
        "PIC16ENHANCED": "PIC16F1509_STUB",
        "ARM_MPU": "ATSAME70_STUB",
        "PIC32MZ": "PIC32MZ2048EFH_STUB",
        "DSPIC30F": "DSPIC30F5011_STUB",
        "DSPIC33FJ": "DSPIC33FJ256GP710A_STUB",
        "DSPIC33EP": "DSPIC33EP512MU810_STUB",
        "DSPIC33A": "DSPIC33AK128MC106_STUB",
        "AVR": "ATMEGA4809_STUB",
    }
    processor = args.processor or default_processors.get(family, f"{family}_STUB")
    write_address = int(str(args.write_address), 0)
    write_data = bytes.fromhex(str(args.write_hex))

    output = run_stub_demo(family=family, processor=processor, write_address=write_address, write_data=write_data)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())