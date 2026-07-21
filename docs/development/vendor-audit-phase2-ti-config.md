# Phase 2 TI Config-Only Import Result

This records Phase 2 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Decision

No config-only TI imports were selected in this phase.

Phase 1 showed that the relevant TI Tcl files from the pinned TI fork are
already present locally after this repository's path normalization. For example,
upstream files named `tcl/target/ti_mspm33.cfg` map to local files such as
`tcl/target/ti/mspm33.cfg`, and upstream board files named
`tcl/board/ti_lp_em_cc2341.cfg` map to local files such as
`tcl/board/ti/lp-em-cc2341.cfg`.

The right Phase 2 action was therefore validation, not copying.

## Scope Checked

Config-load validation focused on the active TI C2000/XDS100 lane:

| File | Result |
| --- | --- |
| `examples/c2000/tms320f280049-xds100v2.cfg` | Passed config-load check. |
| `examples/c2000/tms320f280049-xds100v3.cfg` | Passed config-load check. |
| `examples/c2000/tms320f28069-xds100v2.cfg` | Passed config-load check. |
| `examples/c2000/tms320f28069-xds100v3.cfg` | Passed config-load check. |
| `examples/c2000/tms320f28m35x-xds100v2.cfg` | Passed config-load check. |
| `examples/c2000/tms320f28m35x-xds100v3.cfg` | Passed config-load check. |
| `examples/program-xds100.cfg` with F28M35x/XDS100v3 variables | Passed config-load check. |
| `examples/program-xds100.cfg` with F28069/XDS100v2 variables | Passed config-load check. |
| `target/ti/tms320f280049.cfg` with `interface/dummy.cfg` | Passed target-only config-load check. |
| `target/ti/tms320f28069.cfg` with `interface/dummy.cfg` | Passed target-only config-load check. |
| `target/ti/tms320f28m35x.cfg` with `interface/dummy.cfg` | Passed target-only config-load check. |

These checks stop before `init`, so they prove Tcl parsing, adapter command
availability, target type availability, and script composition. They do not
prove USB probe access or target hardware attach.

## Validation Commands

OpenOCD binary:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe
```

Commands run:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f280049-xds100v2.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f280049-xds100v3.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f28069-xds100v2.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f28069-xds100v3.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f28m35x-xds100v2.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f examples/c2000/tms320f28m35x-xds100v3.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -c "set TARGET_CONFIG target/ti/tms320f28m35x.cfg" -c "set XDS100_INTERFACE interface/ti/xds100v3.cfg" -f examples/program-xds100.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -c "set TARGET_CONFIG target/ti/tms320f28069.cfg" -c "set XDS100_INTERFACE interface/ti/xds100v2.cfg" -f examples/program-xds100.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/dummy.cfg -f target/ti/tms320f280049.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/dummy.cfg -f target/ti/tms320f28069.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/dummy.cfg -f target/ti/tms320f28m35x.cfg -c shutdown
```

Result: all commands exited with code `0`.

## Documentation Updates

The example documentation now uses the verified command-line order for
`examples/program-xds100.cfg`: set variables before sourcing the wrapper with
`-f`.

Updated files:

| File | Change |
| --- | --- |
| `examples/program-xds100.cfg` | Fixed the header example so `XDS100_INTERFACE` and `TARGET_CONFIG` are set before `-f examples/program-xds100.cfg`. |
| `examples/README.md` | Fixed XDS100 wrapper command examples to use the verified order. |
| `examples/c2000/README.md` | Fixed XDS100 wrapper command example to use the verified order. |

## Phase 2 Conclusion

Phase 2 is complete for the selected TI lane. There are no new standalone Tcl
files to import right now. The existing C2000/XDS100 examples, wrapper, and
target configs load successfully with the packaged OpenOCD binary.

Next useful work is Phase 3: confirm the programmer backend path, beginning with
the existing FTDI-based XDS100v2/v3 support and documenting what is already
covered before considering any C backend changes.
