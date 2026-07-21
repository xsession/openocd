# XDS100 Windows USB driver helper

This folder is copied into the Docker-built Windows OpenOCD package under
`tools/windows/usb-driver/`.

`openocd-xds100v2.ps1` and `openocd-xds100v3.ps1` are the easiest entry
points. They start OpenOCD, detect the common `LIBUSB_ERROR_NOT_FOUND`
driver-binding failure, run the packaged WinUSB installer as Administrator,
then retry OpenOCD after you reconnect USB:

```powershell
..\..\..\openocd-xds100v2.cmd -Serial TI680LHO
..\..\..\openocd-xds100v3.cmd -f interface/ti/xds100v3.cfg -c "adapter speed 1000" -c "init; shutdown"
```

`install-xds100-winusb-mi00.ps1` can also be run directly. It uses the
packaged libwdi `wdi-simple.exe` to bind only the selected XDS100 debug
interface to WinUSB:

```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File .\install-xds100-winusb-mi00.ps1 -ProbeVersion v3'
```

The target USB identities are:

| Probe | Debug interface |
| --- | --- |
| XDS100v2 | `VID_0403&PID_A6D0&MI_00` |
| XDS100v3 | `VID_0403&PID_A6D1&MI_00` |

Do not bind `MI_01` to WinUSB; that is normally the auxiliary serial port.

For manual setup, run `bin\x64\zadig.exe`, enable **Options > List All
Devices**, select `XDS100 Class Debug Port` / `MI_00`, and install `WinUSB`.

The Docker build compiles Zadig and `wdi-simple.exe` from
`pbatard/libwdi` tag `v1.5.1`. The package includes libwdi license files under
`libwdi/`.
