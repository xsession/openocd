from pathlib import Path

from dspic_svd.renode import parse_repl_ranges, validate_renode_tree


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_repl_range_parser(tmp_path: Path):
    repl = tmp_path / "device.repl"
    _write(
        repl,
        """
flash: Memory.MappedMemory @ sysbus 0x100000
    size: 0x1000
uart1: UART.dsPIC33_UART @ sysbus <0x220, +0x0A>
""",
    )
    ranges = parse_repl_ranges(repl)
    assert any(item.name == "flash" and item.start == 0x100000 and item.end == 0x101000 for item in ranges)
    assert any(item.name == "uart1" and item.start == 0x220 and item.end == 0x22A for item in ranges)


def test_custom_cores_static_checker_reports_incomplete_branch(tmp_path: Path):
    _write(tmp_path / "build.sh", "CORES=(arm.le dspic33.le)\n")
    _write(
        tmp_path / "src/Infrastructure/src/Emulator/Cores/dsPIC33/dsPIC33.cs",
        '''
public override string Architecture => "dspic33";
public override string GDBArchitecture => "dspic33";
public override List<GDBFeatureDescriptor> GDBFeatures => new List<GDBFeatureDescriptor>();
private int FindBestInterrupt() { return 0; }
''',
    )
    _write(
        tmp_path / "src/Infrastructure/src/Emulator/Cores/dsPIC33/dsPIC33Registers.cs",
        "dsPIC33Registers.W0 dsPIC33Registers.W15 dsPIC33Registers.PC dsPIC33Registers.STATUS\n",
    )
    _write(
        tmp_path / "platforms/cpus/microchip/dspic30f5011.repl",
        'cpu: CPU.DSPIC33 @ sysbus\n    cpuType: "dspic30f5011"\n',
    )
    _write(
        tmp_path / "platforms/cpus/microchip/dspic33fj128gm802.repl",
        'cpu: CPU.DSPIC33 @ sysbus\n    cpuType: "dspic33fj128gm802"\n',
    )

    diagnostics = validate_renode_tree(tmp_path)
    codes = {item.code for item in diagnostics}
    assert "RENODE_TLIB_NOT_BUILT" not in codes
    assert "RENODE_EMPTY_GDB_FEATURES" in codes
    assert "RENODE_INTERRUPT_STUB" in codes
    assert "RENODE_NEAR_MATCH_ONLY" in codes
    assert sum(item.code == "RENODE_PLATFORM_MISSING" for item in diagnostics) == 3
