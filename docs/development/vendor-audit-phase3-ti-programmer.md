# Phase 3 TI Programmer Backend Result

This records Phase 3 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Decision

No new programmer adapter driver is needed for this lane.

The selected TI probe families are already covered by existing OpenOCD
backends:

| Probe | Backend | Transport | Config |
| --- | --- | --- | --- |
| XDS100v2 | `ftdi` | JTAG | `interface/ti/xds100v2.cfg` |
| XDS100v3 | `ftdi` | JTAG | `interface/ti/xds100v3.cfg` |
| XDS100v2/v3 auto | `ftdi` | JTAG | `interface/ti/xds100.cfg` |
| XDS110 | `xds110` | JTAG/SWD | `interface/ti/xds110.cfg` |

The packaged OpenOCD binary reports all of these as built.

## Validation Commands

OpenOCD binary:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe
```

Support matrix:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "adapter ti list" -c shutdown
```

Result summary:

```text
XDS100v2  backend=ftdi    built=yes transport=jtag
XDS100v3  backend=ftdi    built=yes transport=jtag
XDS110    backend=xds110  built=yes transport=jtag/swd/cjtag
```

Interface config-load checks:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds100v2.cfg -c "adapter speed 1000" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds100v3.cfg -c "adapter speed 1000" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds110.cfg -c "adapter speed 1000" -c shutdown
```

Result: all config-load checks exited with code `0`.

Adapter-open attempts:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds100v2.cfg -c "adapter speed 1000" -c "init; shutdown"
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds100v3.cfg -c "adapter speed 1000" -c "init; shutdown"
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/ti/xds110.cfg -c "adapter speed 1000" -c "init; shutdown"
```

Observed results:

| Probe config | Result |
| --- | --- |
| `interface/ti/xds100v2.cfg` | `unable to open ftdi device with description '*', serial '*' at bus location '*'` |
| `interface/ti/xds100v3.cfg` | `libusb_open() failed with LIBUSB_ERROR_NOT_FOUND`; then FTDI open failed. |
| `interface/ti/xds110.cfg` | `XDS110: failed to connect` |

These failures are host/probe availability or driver-binding boundaries, not
missing OpenOCD backend support. Phase 4 should repeat the hardware attach with
the intended probe connected and bound to the correct driver.

Windows PnP enumeration with `Get-PnpDevice -PresentOnly` was attempted but the
sandbox returned `Access denied`, so OpenOCD's own adapter-open errors are the
recorded probe visibility signal for this phase.

## Driver And Permission Updates

Existing documentation already covers XDS100:

- `docs/usage/xds100.md`
- `tools/ti/windows/README.md`
- `udev/99-openocd-xds100.rules`

Phase 3 added:

| File | Change |
| --- | --- |
| `docs/usage/xds110.md` | Added beginner usage, serial selection, speed, probe commands, Linux permissions, and Windows driver notes for XDS110. |
| `udev/99-openocd-probes.rules` | Added XDS110 USB IDs `0451:bef3`, `0451:bef4`, and `1cbe:02a5`. |

## Phase 3 Conclusion

Phase 3 is complete for the selected TI lane. The programmer path uses existing
backends:

- XDS100v2/v3 use the FTDI backend.
- XDS110 uses the native XDS110 backend.
- No new adapter C driver or build registration is required.

The remaining work is hardware attach through the selected probe, which belongs
to Phase 4.
