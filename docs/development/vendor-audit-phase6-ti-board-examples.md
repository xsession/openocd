# Phase 6 TI Board Files And Examples Result

This records Phase 6 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Decision

Add board files for the XDS100v2 and XDS100v3 C2000 combinations, and keep all
examples discovery-only.

Phase 5 deferred flash support until real hardware attach, C28x debug transport,
safe RAM reads, and flash-sector behavior are verified.  Therefore Phase 6 adds
no flash banks and no programming examples.

## Board Files Added

| Board file | Target | Probe |
| --- | --- | --- |
| `board/ti/tms320f280049-xds100v2.cfg` | TMS320F280049 | XDS100v2 |
| `board/ti/tms320f280049-xds100v3.cfg` | TMS320F280049 | XDS100v3 |
| `board/ti/tms320f28069-xds100v2.cfg` | TMS320F28069 | XDS100v2 |
| `board/ti/tms320f28069-xds100v3.cfg` | TMS320F28069 | XDS100v3 |
| `board/ti/tms320f28m35x-xds100v2.cfg` | TMS320F28M35x Concerto | XDS100v2 |
| `board/ti/tms320f28m35x-xds100v3.cfg` | TMS320F28M35x Concerto | XDS100v3 |

Each file:

- sources the matching `interface/ti/xds100v2.cfg` or
  `interface/ti/xds100v3.cfg`;
- selects JTAG transport;
- starts at `adapter speed 1000`;
- sources the matching target config;
- does not define flash banks;
- does not erase, program, unlock, or alter security state.

## Examples Updated

The files under `examples/c2000/` now source the canonical board files instead
of duplicating interface and target setup.  This keeps beginner examples short
and makes board files the reusable path for command-line use.

`examples/c2000/README.md` now omits flash/programming examples and explicitly
states that flash commands are blocked until hardware verification is complete.

## Validation

Board-file config-load validation:

```powershell
$files = @(
  'tms320f280049-xds100v2.cfg',
  'tms320f280049-xds100v3.cfg',
  'tms320f28069-xds100v2.cfg',
  'tms320f28069-xds100v3.cfg',
  'tms320f28m35x-xds100v2.cfg',
  'tms320f28m35x-xds100v3.cfg'
)
foreach ($f in $files) {
  .\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f "board/ti/$f" -c shutdown
}
```

Result: all six board files loaded and exited with code `0`.

Example config-load validation:

```powershell
$files = Get-ChildItem .\examples\c2000\*xds100*.cfg
foreach ($file in $files) {
  .\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f "examples/c2000/$($file.Name)" -c shutdown
}
```

Result: all six example files loaded and exited with code `0`.

## First-Attach Commands

Use these as discovery-only commands on hardware:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v3.cmd `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c "init; scan_chain; c2000_icepick_read_idcode; c2000_icepick_read_code; c2000_icepick_scan_sdtaps; shutdown"
```

If first attach is unstable, lower the speed before init:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v3.cmd `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c "adapter speed 100" `
  -c "init; scan_chain; c2000_icepick_read_idcode; c2000_icepick_scan_sdtaps; shutdown"
```

## Phase 6 Conclusion

Phase 6 is complete:

- XDS100v2/XDS100v3 board files now exist for the C2000 target set.
- Examples reuse the board files.
- All new board and example configs load successfully.
- Examples remain non-destructive and discovery-only.
- Flash commands remain blocked until Phase 5 hardware gates are satisfied.
