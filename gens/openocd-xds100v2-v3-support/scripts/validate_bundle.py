#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    v2 = (root / "overlay/tcl/interface/ftdi/xds100v2.cfg").read_text(encoding="utf-8")
    v3 = (root / "overlay/tcl/interface/ftdi/xds100v3.cfg").read_text(encoding="utf-8")
    auto = (root / "overlay/tcl/interface/ftdi/xds100.cfg").read_text(encoding="utf-8")
    source_tool = (root / "scripts/apply_xds100_support.py").read_text(encoding="utf-8")
    rules = (root / "overlay/udev/99-openocd-xds100.rules").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    require("0xa6d0" in v2 and "0x6010" in v2, "XDS100v2 USB IDs")
    require("0xa6d1" in v3, "XDS100v3 USB ID")
    require(all(pid in auto for pid in ("0xa6d0", "0xa6d1", "0x6010")), "auto-select USB IDs")
    require("ftdi channel 0" in v2 and "transport select jtag" in v2, "FTDI channel A/JTAG selection")
    require("ftdi layout_init 0x0038 0x597b" in v2, "XDS100 GPIO layout")
    require("ftdi initial_signal PWR_RST 1" in v2, "pre-scan PWR_RST transition")
    require("jtag arp_init" in v2, "runtime power-cycle recovery")

    require("ftdi_handle_initial_signal_command" in source_tool, "source patch handler")
    require("mpsse_flush(mpsse_ctx)" in source_tool, "committed low GPIO state")
    require("physical edge" in source_tool, "physical edge rationale")
    require("free(swd_cmd_queue)" in source_tool and "free(ftdi_device_desc)" in source_tool,
            "current and legacy cleanup layouts")

    require('idProduct}=="a6d0"' in rules and 'idProduct}=="a6d1"' in rules, "udev IDs")
    require("--enable-ftdi" in readme, "FTDI build documentation")
    require("scan-only" in readme.lower(), "safe scan-first workflow documentation")

    expected_examples = {
        "tms320f28069": "target/ti/tms320f28069.cfg",
        "tms320f280049": "target/ti/tms320f280049.cfg",
        "tms320f28m35x": "target/ti/tms320f28m35x.cfg",
    }
    for device, target in expected_examples.items():
        for revision in ("v2", "v3"):
            path = root / f"examples/c2000/{device}-xds100{revision}.cfg"
            require(path.is_file(), f"{device} XDS100{revision} example")
            text = path.read_text(encoding="utf-8")
            require(f"interface/ftdi/xds100{revision}.cfg" in text, f"{path.name} interface")
            require(target in text, f"{path.name} target")

    for script in (
        "scripts/program-xds100.sh",
        "scripts/program-xds100.ps1",
        "scripts/test-xds100-openocd.sh",
        "scripts/test-xds100-openocd.ps1",
    ):
        require((root / script).is_file(), script)

    print("Bundle validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
