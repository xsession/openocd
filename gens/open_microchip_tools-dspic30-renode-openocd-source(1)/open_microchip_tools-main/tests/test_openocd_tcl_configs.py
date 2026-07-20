from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


TCLSH = shutil.which("tclsh")
OVERLAY_TCL = Path(__file__).parents[1] / "openocd" / "overlay" / "tcl"


@pytest.mark.skipif(TCLSH is None, reason="tclsh is not installed")
@pytest.mark.parametrize(
    ("target_config", "setup", "processor", "expected_flash_call"),
    [
        (
            "target/mchp-ri4.cfg",
            "set MCHP_RI4_PROCESSOR PIC18F47Q10\nset MCHP_RI4_SCRIPTS scripts.xml",
            "PIC18F47Q10",
            None,
        ),
        (
            "target/mchp-renode.cfg",
            "set MCHP_RENODE_PROCESSOR PIC16",
            "PIC16",
            "flash bank mchp.flash mchp_ri4 0 0x4000 1 1 mchp.cpu 0",
        ),
        (
            "target/mchp-renode.cfg",
            "set MCHP_RENODE_PROCESSOR PIC18",
            "PIC18",
            "flash bank mchp.flash mchp_ri4 0 0x20000 1 1 mchp.cpu 0",
        ),
        (
            "target/mchp-renode.cfg",
            "set MCHP_RENODE_PROCESSOR dsPIC30F5011",
            "dsPIC30F5011",
            "flash bank mchp.flash mchp_ri4 0x100000 0xAC00 1 1 mchp.cpu 0",
        ),
        (
            "target/mchp-renode.cfg",
            "set MCHP_RENODE_PROCESSOR dsPIC33",
            "dsPIC33",
            "flash bank mchp.flash mchp_ri4 0 0x40000 1 1 mchp.cpu 0",
        ),
    ],
)
def test_target_configs_create_virtual_tap_and_parse_with_tcl(
    target_config: str,
    setup: str,
    processor: str,
    expected_flash_call: str | None,
) -> None:
    script = f"""
set calls {{}}
proc adapter {{args}} {{ lappend ::calls [linsert $args 0 adapter] }}
proc transport {{args}} {{ lappend ::calls [linsert $args 0 transport] }}
proc jtag {{args}} {{ lappend ::calls [linsert $args 0 jtag] }}
proc target {{args}} {{ lappend ::calls [linsert $args 0 target] }}
proc flash {{args}} {{ lappend ::calls [linsert $args 0 flash] }}
proc mchp_ri4 {{args}} {{ lappend ::calls [linsert $args 0 mchp_ri4] }}
proc find {{path}} {{ return [file join $::env(MCHP_OVERLAY_TCL) $path] }}
{setup}
source [find {target_config}]
set before [llength $calls]
jtag_init
init_reset run
puts "NOOP_DELTA=[expr {{[llength $calls] - $before}}]"
foreach call $calls {{ puts $call }}
"""
    env = os.environ.copy()
    env["MCHP_OVERLAY_TCL"] = str(OVERLAY_TCL)
    result = subprocess.run(
        [TCLSH],
        input=script,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert "NOOP_DELTA=0" in lines
    assert "adapter driver dummy" in lines
    assert "transport select jtag" in lines
    assert "jtag newtap mchp bridge -irlen 1" in lines
    assert (
        "target create mchp.cpu mchp_ri4_bridge -endian little "
        "-chain-position mchp.bridge"
    ) in lines
    configure = next(line for line in lines if line.startswith("mchp_ri4 configure"))
    assert f"-processor {processor}" in configure
    flash_calls = [line for line in lines if line.startswith("flash bank")]
    assert flash_calls == ([] if expected_flash_call is None else [expected_flash_call])


def test_target_config_documents_current_openocd_chain_position_requirement() -> None:
    target_text = (OVERLAY_TCL / "target" / "mchp-ri4.cfg").read_text(encoding="utf-8")
    interface_text = (OVERLAY_TCL / "interface" / "mchp-ri4.cfg").read_text(encoding="utf-8")

    assert "jtag newtap $CHIPNAME $MCHP_RI4_TAPNAME -irlen 1" in target_text
    assert "-chain-position $_MCHP_RI4_CHAIN_POSITION" in target_text
    assert "proc jtag_init {}" in interface_text
    assert "proc init_reset {mode}" in interface_text


def test_target_driver_does_not_compare_copied_target_type_by_pointer() -> None:
    source = (
        Path(__file__).parents[1]
        / "openocd"
        / "overlay"
        / "src"
        / "target"
        / "mchp_ri4_bridge.c"
    ).read_text(encoding="utf-8")

    assert "target->type != &mchp_ri4_bridge_target" not in source
    assert "strcmp(target->type->name, MCHP_RI4_TARGET_NAME) == 0" in source
