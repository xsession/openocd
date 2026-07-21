# Phase 7 TI Build And Regression Validation Result

This records Phase 7 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Native Build

Native configure was run from `build-native` with the TI-relevant adapters
enabled:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command `
  "& 'C:\msys64\usr\bin\bash.exe' -lc 'cd /c/Users/livanyi/Desktop/WORK/GIT/openocd/build-native && PATH=/mingw64/bin:$PATH ../configure --enable-internal-jimtcl --disable-werror --disable-doxygen-html --disable-doxygen-pdf --disable-buspirate'"
```

`--disable-buspirate` was added after a broad native build failed in the
unrelated Bus Pirate serial adapter with:

```text
fatal error: termios.h: No such file or directory
```

The Bus Pirate adapter is not part of the TI C2000/XDS100/XDS110 lane.  The
final configure summary kept the required TI path enabled:

```text
MPSSE mode of FTDI based devices                 yes
TI XDS110 Debug Probe                            yes
Dummy Adapter                                    yes
Bus Pirate                                       no
```

Native build:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command `
  "& 'C:\msys64\usr\bin\bash.exe' -lc 'cd /c/Users/livanyi/Desktop/WORK/GIT/openocd/build-native && PATH=/mingw64/bin:$PATH make -j4'"
```

Result: passed.  The build produced:

```text
build-native/src/openocd.exe
```

## Built-Binary Validation

The built binary requires MinGW runtime DLLs on `PATH` when launched from
PowerShell:

```powershell
$env:PATH='C:\msys64\mingw64\bin;' + $env:PATH
```

TI adapter matrix:

```powershell
.\build-native\src\openocd.exe -c "adapter ti list" -c shutdown
```

Result summary:

```text
XDS100v2  backend=ftdi    built=yes
XDS100v3  backend=ftdi    built=yes
XDS110    backend=xds110  built=yes
```

F28M35x target creation:

```powershell
.\build-native\src\openocd.exe -s .\tcl -c "adapter driver dummy" `
  -f target/ti/tms320f28m35x.cfg `
  -c "targets" `
  -c shutdown
```

Result:

```text
tms320f28m35x.c28x  c28x  little  tms320f28m35x.icepick  unknown
```

All six new C2000 XDS100 board files loaded with `-c shutdown`.
All six `examples/c2000/*xds100*.cfg` files loaded with `-c shutdown`.

## Unrelated Config Regression

These existing board configs were loaded with the freshly built binary:

```text
board/ti/ek-tm4c123gxl.cfg
board/ti/cc26x2-launchpad.cfg
board/ti/mspm0c1103-xds110.cfg
board/st_nucleo_f4.cfg
```

Result: all exited with code `0`.

## Windows Package Build

The Windows cross-package build was run through Docker Buildx:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command `
  "& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' buildx build --platform linux/amd64 -f docker/Dockerfile.windows-cross --build-arg JOBS=0 --build-arg CONFIGURE_FLAGS='--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-libjaylink --enable-jimtcl-maintainer --enable-internal-jimtcl' --target export --output type=local,dest=artifacts/windows ."
```

Result: passed.  The build exported:

```text
artifacts/windows/openocd-windows-x86_64/
artifacts/windows/openocd-windows-x86_64.zip
```

Package validation:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -c "adapter ti list" `
  -c shutdown
```

Result: XDS100v2, XDS100v3, and XDS110 report `built=yes`.

All six packaged C2000 XDS100 board files loaded with `-c shutdown`.

The package contains:

```text
openocd-xds100v2.cmd
openocd-xds100v3.cmd
tools/windows/usb-driver/install-xds100-winusb-mi00.ps1
tools/windows/usb-driver/openocd-xds100.ps1
```

## Wrapper Regression

Phase 7 found and fixed one wrapper parsing issue: passing OpenOCD-style `-s`
to `openocd-xds100v3.cmd` was ambiguous with wrapper parameters.  The wrapper
now accepts `-s` as an alias for `-Scripts`.

Validation command:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v3.cmd `
  -NoAutoInstall `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c "init; shutdown"
```

Result: command-line parsing works.  The command reaches OpenOCD and then fails
at the expected hardware/driver boundary:

```text
libusb_open() failed with LIBUSB_ERROR_NOT_FOUND
unable to open ftdi device with description '*', serial '*' at bus location '*'
TI XDS100 on Windows needs a libusb-compatible driver on FTDI interface MI_00 only.
For XDS100v3, bind VID_0403&PID_A6D1&MI_00 to WinUSB; packaged helper: openocd-xds100v3.cmd
Leave MI_01 on the vendor/VCP driver if you use the probe's UART channel.
```

## Hardware And Flash Validation

Real hardware attach was not available in this validation run.  The recorded
adapter-open result remains the host/probe driver boundary above.

Flash validation was intentionally not run.  Phase 5 blocks destructive flash
checks until a real board passes:

```text
scan_chain
c2000_icepick_read_idcode
c2000_icepick_scan_sdtaps
halt
reg
mdw <known_safe_ram_address> 4
```

## Phase 7 Conclusion

Phase 7 is complete:

- native build passed with the unrelated Bus Pirate adapter disabled;
- the freshly built binary validates the TI adapter matrix and C28x target
  creation;
- all new board and example configs load;
- selected unrelated board configs still load;
- Windows package build passed;
- packaged XDS100 helpers and board files are present;
- the XDS100 wrapper now handles `-s` correctly;
- hardware and flash checks remain explicitly gated on real hardware access.
