# OpenOCD XDS100v2 / LAUNCHXL-F28069M chat record - 2026-07-21

This document records the debugging work, repository changes, and current
hardware status from the XDS100v2 and LAUNCHXL-F28069M session. It is an
engineering summary of the chat rather than a verbatim transcript.

## Starting point

The connected probe was initially visible to Windows as a TI XDS100v2 device,
but OpenOCD could not enumerate the target. The active board was later confirmed
to be a Texas Instruments LAUNCHXL-F28069M LaunchPad with an onboard XDS100v2
debug probe and a separate auxiliary serial port.

Windows Device Manager showed two XDS100 functions:

- `XDS100 Class Debug Port`: JTAG/debug interface, FTDI channel A, USB interface
  `MI_00`.
- `XDS100 Class Auxiliary Port`: UART/auxiliary interface, FTDI channel B, USB
  interface `MI_01`.

The local probe serial reported by TI tooling was:

```text
TI680LHO
```

The auxiliary serial port appeared locally as:

```text
COM19
```

## Probe and serial checks

The project-local scanner was run against the attached XDS100v2:

```powershell
.\tools\ti\xds100v2_detect.ps1 -LogFile .\artifacts\xds100v2-detect.log
```

It found the XDS100v2 USB composite device and reported the Windows driver
binding:

```text
XDS100 Class USB Serial Port (COM19)
XDS100 Class Debug Port
XDS100 Class Auxiliary Port
```

TI's `xds100serial.exe` also identified the probe:

```text
VID/PID    Type            Serial #    Description
0403/a6d0  XDS100v1/v2     TI680LHO    Texas Instruments Inc.XDS100 Ver 2.0
```

The auxiliary UART path was checked by opening `COM19` at 115200 baud. The port
opened successfully, with no buffered text waiting at that baud rate. This
confirms that the USB composite device and auxiliary serial interface are
enumerating cleanly.

## CCS target checks

The CCS fallback detector was run first against several likely C2000 targets,
then narrowed to the board's known MCU:

```powershell
.\tools\ti\xds100v2_ccs_detect.ps1 -Serial TI680LHO -Candidates f28069
.\tools\ti\xds100v2_ccs_detect.ps1 -Serial TI680LHO -Candidates f28069 -Tclk 100KHz
```

Both the normal and slower-clock F28069 checks reached CCS register database
setup and failed only when connecting to the C28x core:

```text
C28xx: Error connecting to the target: (Error -1135 @ 0x0)
The debug probe reported an error.
```

The generated CCS `.ccxml` path is:

```text
artifacts\xds100v2-ccs-detect\f28069.ccxml
```

The per-run CCS log is:

```text
artifacts\xds100v2-ccs-detect\f28069.log
```

## OpenOCD checks

A packaged Windows OpenOCD binary was found under:

```text
dist\windows\openocd-windows-x86_64\bin\openocd.exe
```

The new board config was tried with:

```powershell
.\dist\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f board\ti\launchxl-f28069m-xds100v2.cfg `
  -c "adapter serial TI680LHO" `
  -c "init" `
  -c "scan_chain" `
  -c "shutdown"
```

Two software-side issues were discovered:

- `tcl/interface/ftdi/xds100v2.cfg` used `ftdi initial_signal`, which is not
  available in the packaged OpenOCD build. The command is now wrapped in
  `catch`.
- The packaged binary does not include the project-local `c28x` target type, so
  it stops with `Unknown target type c28x` when using the full F28069 board
  configuration.

The lower-level XDS100v2 scan that avoids the C28x target type still cannot open
the FTDI debug interface while Windows binds it to TI's debug-probe driver:

```text
libusb_open() failed with LIBUSB_ERROR_NOT_FOUND
unable to open ftdi device with description '*', serial 'TI680LHO'
```

This means OpenOCD/libftdi needs only the XDS100 debug interface (`MI_00`) bound
to a WinUSB/libusb-compatible driver. The auxiliary serial interface should stay
on the TI/FTDI serial driver.

## Repository changes made

The session added a board-level OpenOCD configuration:

```text
tcl/board/ti/launchxl-f28069m-xds100v2.cfg
```

That file sources:

```text
interface/ti/xds100v2.cfg
target/ti/tms320f28069.cfg
```

The TI README was updated with the LAUNCHXL-F28069M-specific probe layout,
serial number, COM port, commands, and troubleshooting notes:

```text
tools/ti/README.md
```

The XDS100 and C2000 docs were updated to mention the new board config:

```text
docs/usage/xds100.md
docs/targets/ti-c2000-support.md
```

The CCS detector was improved:

```text
tools/ti/xds100v2_ccs_detect.ps1
```

Changes include:

- F28069-style `.ccxml` generation that uses only the C28x and CLA XDS100v2
  drivers for simple C2000 targets.
- Optional `-Tclk` support, tested with `100KHz`.
- LAUNCHXL-F28069M-specific guidance when CCS reports `Error -1135`.

The XDS100v2 FTDI config was made compatible with older OpenOCD binaries:

```text
tcl/interface/ftdi/xds100v2.cfg
```

## Current diagnosis

The USB side is healthy:

- Windows sees the XDS100v2 debug and auxiliary interfaces.
- TI's `xds100serial.exe` sees the probe and serial number.
- `COM19` opens successfully as the auxiliary UART.

The CCS side reaches the correct F28069 target setup, then fails at C28x
connection with `Error -1135`.

The OpenOCD side has two separate blockers:

- The currently packaged OpenOCD binary lacks the new `c28x` target type and
  must be rebuilt before the board config can fully load.
- OpenOCD/libftdi cannot open the XDS100 debug interface until `MI_00` is bound
  to a WinUSB/libusb-compatible driver.

## Likely physical fix

For LAUNCHXL-F28069M, the likely cause of CCS `Error -1135` is board switch or
power-domain setup:

- Set `S1.3` / `TRST` to `ON` / up. TRST disables JTAG when it is off.
- Populate `JP1` and `JP2` when powering the board only from USB, so both
  isolated power domains are powered.
- For the serial path, use `COM19`; the LaunchPad serial mux expects `JP7`
  populated and `JP6` open.
- After changing switches or jumpers, unplug and reconnect USB before rerunning
  CCS or OpenOCD.

## Next commands

After checking the physical switch and jumper state:

```powershell
.\tools\ti\xds100v2_ccs_detect.ps1 -Serial TI680LHO -Candidates f28069 -Tclk 100KHz
```

After rebinding only `MI_00` to WinUSB/libusb and rebuilding OpenOCD with the
project-local C28x target support:

```powershell
openocd -f board/ti/launchxl-f28069m-xds100v2.cfg -c "adapter serial TI680LHO"
```

## Validation performed

The repository whitespace check passed:

```powershell
git diff --check
```

The check emitted only normal line-ending conversion warnings for edited text
files.
