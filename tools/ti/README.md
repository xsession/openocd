# TI tooling

This directory contains project-local Texas Instruments helpers that support the
OpenOCD TI target, adapter, SVD, and serial-programming work.

OpenOCD-side TI probe configs live under `tcl/interface/ti/`. A built OpenOCD
binary can report its compiled-in TI adapter support with `adapter ti list`.

## Contents

- `flash_f28004x_serial.ps1` wraps TI's external C2000Ware
  `serial_flash_programmer.exe` for F28004x SCI boot-format images.
- `xds100v2_detect.ps1` performs a non-destructive XDS100v2 USB/JTAG scan and
  reports whether Windows has the probe bound to a driver OpenOCD can use.
- `xds100v2_ccs_detect.ps1` uses TI CCS `DSLite.exe` with generated `.ccxml`
  files to test likely C2000 MCU targets through the stock TI XDS100v2 driver.
- `c2000_toolchain/` is a curated source-only import of the TI C2000/MSPM0
  generator, debug adapter, CCS bridge, Renode examples, and validation tooling
  from `gens/ti-c2000-toolchain-0.3.0`.

OpenOCD runtime target and adapter support remains in `src/`, `tcl/`, `udev/`,
and `examples/`.

## LAUNCHXL-F28069M XDS100v2

Use the local probe scanner first:

```powershell
.\tools\ti\xds100v2_detect.ps1 -LogFile .\artifacts\xds100v2-detect.log
```

On the current workstation the connected probe reports as:

```text
0403/a6d0  XDS100v1/v2  TI680LHO  Texas Instruments Inc.XDS100 Ver 2.0
```

The connected board is a LAUNCHXL-F28069M. Windows exposes the onboard XDS100v2
as two functions:

- `XDS100 Class Debug Port`: FTDI channel A / USB interface `MI_00`, used for
  JTAG.
- `XDS100 Class Auxiliary Port`: FTDI channel B / USB interface `MI_01`, used
  as the board serial port. On the current machine this appeared as `COM19`.

Use the board config for OpenOCD:

```powershell
openocd -f board/ti/launchxl-f28069m-xds100v2.cfg
```

If more than one XDS100 probe is connected, select this board by serial:

```powershell
openocd -f board/ti/launchxl-f28069m-xds100v2.cfg -c "adapter serial TI680LHO"
```

OpenOCD cannot enumerate the JTAG chain while Windows binds interface 0 to
`TI_Debug_Probe`; libusb reports `LIBUSB_ERROR_NOT_FOUND`. Rebind only the debug
interface (`MI_00`) to a WinUSB/libusb-compatible driver before using OpenOCD
with `interface/ti/xds100v2.cfg`. The auxiliary serial interface can remain on
the TI/FTDI serial driver.

The CCS-based fallback test is:

```powershell
.\tools\ti\xds100v2_ccs_detect.ps1 -Serial TI680LHO
```

The target MCU is `TMS320F28069M`, so the useful CCS probe test is:

```powershell
.\tools\ti\xds100v2_ccs_detect.ps1 -Serial TI680LHO -Candidates f28069
```

The earlier broad local pass tested `f280049`, `f280049c`, `f28069`, `f28035`,
and `f28m35h52c1`; none connected successfully. A narrow LAUNCHXL-F28069M pass
with only `f28069` also failed in CCS with:

```text
C28xx: Error connecting to the target: (Error -1135 @ 0x0)
The debug probe reported an error.
```

With the board now identified, debugging should focus on the F28069 JTAG path,
target power/boot mode, and the Windows driver binding for the XDS100 debug
interface.

For this specific LaunchPad, check the hardware before changing software:

- Set `S1.3` / `TRST` to `ON` / up. If TRST is off, the debugger cannot connect
  to the MCU even though the XDS100v2 USB device and serial port enumerate.
- Populate `JP1` and `JP2` when powering the board only from USB; the board has
  isolated power domains and both sides must be powered for JTAG.
- For the serial path, use the auxiliary port (`COM19` on this workstation).
  The LaunchPad serial mux expects `JP7` populated and `JP6` open.
- After changing switches or jumpers, unplug/replug USB before rerunning CCS or
  OpenOCD.

The local packaged OpenOCD binary in `dist/windows` is useful for FTDI/JTAG
probing, but it does not include the project-local `c28x` target type yet. A
new build is required before `board/ti/launchxl-f28069m-xds100v2.cfg` can create
the C28x target; otherwise OpenOCD will stop with `Unknown target type c28x`.
