# OpenOCD and XDS100v2/v3

The maintained implementation is under `openocd/`.

## Install

```console
python3 openocd/scripts/apply_xds100_support.py /path/to/openocd
```

Useful modes:

```console
python3 openocd/scripts/apply_xds100_support.py /path/to/openocd --dry-run
python3 openocd/scripts/apply_xds100_support.py /path/to/openocd --check
```

The installer patches `src/jtag/drivers/ftdi.c`, stores a backup on the first
edit, and installs Tcl files, examples, documentation, and udev rules.

## Probe configurations

```text
interface/ftdi/xds100v2.cfg
interface/ftdi/xds100v3.cfg
interface/ftdi/xds100.cfg
```

The auto configuration accepts v2, v3, and generic embedded FT2232H identities.
Prefer a version-specific file and an adapter serial when multiple FTDI devices
are attached.

## First-connection initialization

XDS100 keeps target-side pins isolated after target power loss. The OpenOCD
patch adds:

```text
ftdi initial_signal PWR_RST 1
```

The base GPIO state is physically flushed with `PWR_RST` low, then the signal is
raised before JTAG examination. This avoids a queued low/high sequence that
never reaches the CPLD as a real edge.

## Target-only power cycle

From the OpenOCD telnet console:

```text
xds100_recover_after_target_power_cycle
```

## C2000 examples

```text
openocd/examples/c2000/tms320f28069-xds100v2.cfg
openocd/examples/c2000/tms320f28069-xds100v3.cfg
openocd/examples/c2000/tms320f280049-xds100v2.cfg
openocd/examples/c2000/tms320f280049-xds100v3.cfg
openocd/examples/c2000/tms320f28m35x-xds100v2.cfg
openocd/examples/c2000/tms320f28m35x-xds100v3.cfg
```

## Windows driver note

OpenOCD requires a libusb-compatible driver on FTDI channel A. XDS100 commonly
uses channel A for JTAG and channel B for UART. Do not replace the UART channel
driver when serial-console access must remain available.
