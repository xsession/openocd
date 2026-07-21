# TI XDS100v2 And XDS100v3 Programmer Support

This page records the support status for TI XDS100v2 and XDS100v3 probes in
this fork.

## Support Status

| Item | Status |
| --- | --- |
| Backend | Existing OpenOCD `ftdi` adapter driver |
| Transport | JTAG |
| XDS100v2 config | `interface/ti/xds100v2.cfg` |
| XDS100v3 config | `interface/ti/xds100v3.cfg` |
| Auto config | `interface/ti/xds100.cfg` |
| Windows package helpers | `openocd-xds100v2.cmd`, `openocd-xds100v3.cmd` |
| Linux permissions | `udev/99-openocd-xds100.rules` |

XDS100v2 and XDS100v3 are FTDI/MPSSE probes.  OpenOCD claims FTDI interface
`MI_00` for JTAG and leaves `MI_01` available for UART/auxiliary use.

## Windows Driver Binding

The Windows package includes libwdi/Zadig tools and wrapper scripts.  The
wrapper runs OpenOCD once, detects the common FTDI/libusb open failure, launches
the WinUSB installer as Administrator for `MI_00`, and then asks the user to
reconnect the probe.

Use:

```powershell
.\openocd-xds100v2.cmd -f board/ti/tms320f28069-xds100v2.cfg -c "init; shutdown"
.\openocd-xds100v3.cmd -f board/ti/tms320f28m35x-xds100v3.cfg -c "init; shutdown"
```

The wrapper also accepts OpenOCD-style `-s`:

```powershell
.\openocd-xds100v3.cmd -s .\share\openocd\scripts -f board/ti/tms320f28m35x-xds100v3.cfg -c "init; shutdown"
```

Expected driver-boundary error before WinUSB is installed:

```text
TI XDS100 on Windows needs a libusb-compatible driver on FTDI interface MI_00 only.
For XDS100v3, bind VID_0403&PID_A6D1&MI_00 to WinUSB; packaged helper: openocd-xds100v3.cmd
Leave MI_01 on the vendor/VCP driver if you use the probe's UART channel.
```

## C2000 Board Files

Discovery-only board files are available for the active C2000 lane:

```text
board/ti/tms320f280049-xds100v2.cfg
board/ti/tms320f280049-xds100v3.cfg
board/ti/tms320f28069-xds100v2.cfg
board/ti/tms320f28069-xds100v3.cfg
board/ti/tms320f28m35x-xds100v2.cfg
board/ti/tms320f28m35x-xds100v3.cfg
```

They are intentionally non-destructive.  They do not define flash banks and do
not erase, program, unlock, or modify device security state.

## Tested Commands

Validated on Windows on July 21, 2026 with:

```text
OpenOCD 0.12.0+dev-snapshot (2026-07-21-10:49)
```

Package validation:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -c "adapter ti list" `
  -c shutdown
```

Result: XDS100v2, XDS100v3, and XDS110 report `built=yes`.

Board validation:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c shutdown
```

Result: config load passed.

## Known Limits

- Real XDS100v2/v3 hardware attach was not completed in this validation run.
- The observed Windows boundary is driver binding: OpenOCD reaches FTDI/libusb
  and reports `LIBUSB_ERROR_NOT_FOUND` when `MI_00` is not bound to WinUSB.
- C2000 CPU debug control remains gated on verified C28x transport opcodes and
  real-board ICEPick secondary-TAP routing.
- Flash programming remains blocked until halt, register reads, safe RAM reads,
  erase/write/verify/protect behavior, and recovery are tested on real hardware.
