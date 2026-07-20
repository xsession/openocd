from __future__ import annotations

import argparse
import json
from typing import Iterable, List, Sequence

from zephyr_pickit4_replacement.pk4_observed_profile import DEFAULT_STATUS_KEYS, Pk4ObservedProbeModel


def build_status_exercise(keys: Sequence[str] | None = None) -> dict:
    probe = Pk4ObservedProbeModel(debug_mode=True, halted=True)
    selected_keys = list(keys) if keys else list(DEFAULT_STATUS_KEYS)
    initial_status = probe.status_snapshot(selected_keys)

    boot_write = probe.write_program(0x00400010, b"BOOT")
    app_write = probe.write_program(0x0040C020, b"APP!")
    app2_write = probe.write_program(0x00500010, b"DAP!")
    relative_app_write = probe.write_program(0x30, b"REL!")

    boot_read = probe.read_program(0x00400010, 4)
    app_read = probe.read_program(0x0040C020, 4)
    app2_read = probe.read_program(0x00500010, 4)
    relative_app_read = probe.read_program(0x30, 4)

    return {
        "status": initial_status,
        "postExerciseStatus": probe.status_snapshot(selected_keys),
        "memoryExercises": {
            "bootWrite": {**boot_write, "dataHex": boot_read["data"].hex()},
            "appWrite": {**app_write, "dataHex": app_read["data"].hex()},
            "app2Write": {**app2_write, "dataHex": app2_read["data"].hex()},
            "relativeAppWrite": {**relative_app_write, "dataHex": relative_app_read["data"].hex()},
        },
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exercise the observed PK4 RI4 status/profile model without a Zephyr build")
    parser.add_argument("keys", nargs="*", help="Optional RI4 status keys to query")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(build_status_exercise(args.keys), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())