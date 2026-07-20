# TI Debug Adapter Support

This fork keeps Texas Instruments probe support local to OpenOCD when the host
protocol is available in C or through an open standard. Use:

```text
adapter ti list
```

to print the compiled-in TI support matrix from the OpenOCD binary.

## Supported local backends

| Probe family | OpenOCD backend | Config |
| --- | --- | --- |
| XDS100v2 | `ftdi` C driver | `interface/ti/xds100v2.cfg` |
| XDS100v3 | `ftdi` C driver | `interface/ti/xds100v3.cfg` |
| XDS100v2/v3 auto | `ftdi` C driver | `interface/ti/xds100.cfg` |
| XDS110 | native `xds110` C driver | `interface/ti/xds110.cfg` |
| TI ICDI | HLA `ti-icdi` C backend | `interface/ti/ti-icdi.cfg` |
| TI CMSIS-DAP probes | CMSIS-DAP C backend | `interface/ti/cmsis-dap.cfg` |

## Unsupported proprietary probe families

XDS200, XDS560, and MSP-FET require TI's proprietary USCIF/DebugServer host
protocol. They are intentionally represented by `interface/ti/xds200.cfg`,
`interface/ti/xds560.cfg`, `interface/ti/msp-fet.cfg`, and
`interface/ti/unsupported-closed.cfg`, which fail with an explicit message
instead of silently pretending OpenOCD can drive them.

## Build flags

A useful local build for TI probes should include:

```console
./configure --enable-ftdi --enable-xds110 --enable-ti-icdi \
  --enable-cmsis-dap --enable-cmsis-dap-v2
```

On Windows, XDS100 FTDI interface 0 must use a libusb-compatible driver for
OpenOCD. Keep the UART/auxiliary interface on its original driver if serial
console access is needed.
