# XDS100v2 Windows USB driver helper

This folder is copied into the Docker-built Windows OpenOCD package under
`tools/windows/usb-driver/`.

`openocd-xds100v2.ps1` is the easiest entry point. It starts OpenOCD with the
LAUNCHXL-F28069M board config, detects the common `LIBUSB_ERROR_NOT_FOUND`
driver-binding failure, runs the packaged WinUSB installer as Administrator,
then retries OpenOCD after you reconnect USB:

```powershell
..\..\..\openocd-xds100v2.cmd -Serial TI680LHO
```

`install-xds100v2-winusb-mi00.ps1` can also be run directly. It uses the
packaged libwdi `wdi-simple.exe` to bind only the XDS100v2 debug interface to
WinUSB:

```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File .\install-xds100v2-winusb-mi00.ps1'
```

The target USB identity is `VID_0403&PID_A6D0&MI_00`. Do not bind
`MI_01` to WinUSB; that is the LaunchPad auxiliary serial port.

For manual setup, run `bin\x64\zadig.exe`, enable **Options > List All
Devices**, select `XDS100 Class Debug Port` / `MI_00`, and install `WinUSB`.

The Docker build compiles Zadig and `wdi-simple.exe` from
`pbatard/libwdi` tag `v1.5.1`. The package includes libwdi license files under
`libwdi/`.
