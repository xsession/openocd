# Phase 8 TI Documentation And Support Status Result

This records Phase 8 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Documentation Added Or Updated

| Area | File |
| --- | --- |
| Target docs | `docs/targets/ti-c2000-support.md` |
| Programmer docs | `docs/programmers/ti-xds100.md` |
| Usage docs | `docs/usage/xds100.md`, `docs/usage/xds110.md` |
| Development status | Phase 1 through Phase 8 result files under `docs/development/` |
| Index | `docs/index.md` |
| Vendor audit | `docs/development/openocd-vendor-fork-audit.md` |

## Tested Environment

Validation was performed on Windows on July 21, 2026.

Native build:

```text
build-native/src/openocd.exe
OpenOCD 0.12.0+dev-g933474840-dirty (2026-07-21-10:33)
```

Windows package build:

```text
artifacts/windows/openocd-windows-x86_64/bin/openocd.exe
OpenOCD 0.12.0+dev-snapshot (2026-07-21-10:49)
```

Validated commands include:

```powershell
.\build-native\src\openocd.exe -c "adapter ti list" -c shutdown
.\build-native\src\openocd.exe -s .\tcl -c "adapter driver dummy" -f target/ti/tms320f28m35x.cfg -c "targets" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts -f board/ti/tms320f28m35x-xds100v3.cfg -c shutdown
```

## Support Status

| Feature | Status |
| --- | --- |
| XDS100v2 backend | Built through OpenOCD `ftdi` |
| XDS100v3 backend | Built through OpenOCD `ftdi` |
| XDS110 backend | Built through OpenOCD `xds110` |
| XDS100 Windows driver helper | Packaged and validated to parse `-s` |
| F28M35x target creation | `c28x` target creation validated with dummy adapter |
| C2000 XDS100 board files | Six board files added and config-load validated |
| C2000 examples | Six examples updated and config-load validated |
| C2000 flash | Deferred |
| Real hardware attach | Not completed in this session |

## Known Limits

- XDS100v2/v3 hardware attach still requires the probe's FTDI `MI_00` interface
  to be bound to WinUSB/libusb on Windows.
- The auxiliary FTDI `MI_01` interface should remain on the vendor/VCP driver
  when used as a UART.
- C28x halt, resume, step, register access, and memory access remain gated on
  verified TI C28x debug transport packets and real-board ICEPick routing.
- F28M35x/C2000 flash commands are intentionally absent until destructive flash
  tests can be run on recoverable hardware.
- XDS200, XDS560, and MSP-FET remain unsupported because they require TI's
  proprietary USCIF/DebugServer protocol.

## Phase 8 Conclusion

Phase 8 is complete.  User-facing target/programmer docs, development status,
tested commands, support boundaries, and index links are now recorded for the
TI C2000/XDS100/XDS110 lane.
