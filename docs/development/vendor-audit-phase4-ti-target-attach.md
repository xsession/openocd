# Phase 4 TI MCU Target Attach Result

This records Phase 4 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Decision

The first MCU target for this lane is the TI F28M35x Concerto family.

F28M35x is a dual-core C2000 device with a Cortex-M3 subsystem and a C28x
subsystem behind a TI ICEPick-C JTAG router.  The current OpenOCD integration
focuses on the C28x path because the repository contains a `c28x` target backend
and C2000 ICEPick discovery helpers.

| Item | Phase 4 decision |
| --- | --- |
| Target family | TI F28M35x Concerto |
| Architecture | Cortex-M3 plus C28x behind ICEPick-C |
| OpenOCD target backend | `c28x` is present and registered |
| Target config | `target/ti/tms320f28m35x.cfg` |
| Probe examples | `examples/c2000/tms320f28m35x-xds100v2.cfg`, `examples/c2000/tms320f28m35x-xds100v3.cfg` |
| Work-area RAM | Not defined yet; keep unset until the exact device memory map is verified |
| Flash support | Not part of Phase 4 |

## Target Configuration

The target file creates the external ICEPick TAP and a C28x OpenOCD target:

```tcl
source [find target/ti/c2000-icepick-scan.cfg]
target create $TARGETNAME c28x -chain-position $C28X_CHAIN_POSITION
c28x device F28M35x-C28x
c28x procid 0x5000A3F8
c28x icepick_port 0x11
```

The target intentionally binds to the visible ICEPick TAP until a hardware
attach confirms the routed secondary C28x TAP.  This keeps the config
non-destructive and useful for first attach.

## Local Validation

OpenOCD binary:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe
```

Target creation:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl `
  -c "adapter driver dummy" `
  -f target/ti/tms320f28m35x.cfg `
  -c "targets" `
  -c "shutdown"
```

Result:

```text
TargetName              Type  Endian  TapName                 State
tms320f28m35x.c28x      c28x  little  tms320f28m35x.icepick   unknown
```

Support-status helper:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl `
  -c "adapter driver dummy" `
  -f target/ti/tms320f28m35x.cfg `
  -c "c2000_support_status" `
  -c "shutdown"
```

Result:

```text
Target: tms320f28m35x
Available now: ICEPick IDCODE, ICEPick code, secondary-TAP discovery and C28x OpenOCD target creation
C28x halt/resume/register/memory operations still require verified TI debug transport packets
Run after init: c2000_icepick_read_idcode; c2000_icepick_read_code; c2000_icepick_scan_sdtaps
```

## Hardware Attach Command

After the XDS100v3 WinUSB binding is installed, use the packaged wrapper so the
driver fix can be offered automatically if the probe is still bound to the wrong
Windows driver:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v3.cmd `
  -f examples/c2000/tms320f28m35x-xds100v3.cfg `
  -c "init; scan_chain; c2000_icepick_read_idcode; c2000_icepick_read_code; c2000_icepick_scan_sdtaps; shutdown"
```

For XDS100v2, use:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v2.cmd `
  -f examples/c2000/tms320f28m35x-xds100v2.cfg `
  -c "init; scan_chain; c2000_icepick_read_idcode; c2000_icepick_read_code; c2000_icepick_scan_sdtaps; shutdown"
```

Expected first successful attach:

- `scan_chain` lists `tms320f28m35x.icepick`.
- `c2000_icepick_read_idcode` returns a nonzero 32-bit ICEPick IDCODE.
- `c2000_icepick_read_code` returns a nonzero 32-bit ICEPick identification
  code.
- `c2000_icepick_scan_sdtaps` reports at least one present secondary TAP.
- `targets` lists `tms320f28m35x.c28x`.

## Debug Operation Gate

Phase 4 does not claim full C28x debug control yet.

These commands must be run only after the ICEPick scan succeeds and the C28x
secondary TAP routing has been verified:

```text
halt
resume
step
reg
mdw <known_safe_ram_address> 4
```

Do not define `work-area-phys`, `work-area-size`, or flash banks until the exact
F28M35x part number and memory map have been confirmed from the data sheet and
the memory read succeeds on hardware.

## Reset And Lock Notes

- Start with `adapter speed 100` or `adapter speed 500` if `adapter speed 1000`
  is unstable.
- Confirm target power and JTAG boot/debug mode before debugging.
- If the device is secured or debug-locked, halt, register, and memory commands
  may fail even when ICEPick discovery works.
- Keep first-attach commands non-destructive: do not erase, program, unlock, or
  run flash commands in Phase 4.

## Phase 4 Conclusion

Phase 4 is complete for repository integration and first-attach preparation:

- The F28M35x architecture and OpenOCD target backend are identified.
- The target Tcl exists and creates the expected `c28x` target.
- Work-area RAM is intentionally unset until hardware memory-map validation.
- Hardware attach commands are recorded for XDS100v2 and XDS100v3.
- The remaining halt/resume/step/register/memory checks are explicitly gated on
  successful ICEPick secondary-TAP discovery with a real board connected.
