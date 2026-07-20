# OpenOCD XDS100v2/XDS100v3 programmer support

This bundle adds reliable TI XDS100v2 and XDS100v3 support to the
`xsession/openocd` fork and compatible current OpenOCD checkouts.

The existing FTDI configuration can identify XDS100 probes, but the XDS100
CPLD keeps its target-side pins isolated while its power-loss latch is set.
Clearing the latch requires a `PWR_RST` low-to-high transition after the FTDI
MPSSE engine opens and before OpenOCD examines the JTAG chain. Historically,
users had to start OpenOCD, set the signal manually, and run `jtag arp_init`.
This bundle makes the first connection deterministic.

## Implemented

- New generic FTDI command:

  ```text
  ftdi initial_signal <name> <0|1|z>
  ```

  The driver commits the layout's initial GPIO state first and then applies all
  configured initial signals before JTAG chain examination, guaranteeing a real
  low-to-high edge on `PWR_RST`.

- XDS100v2 support:
  - `0403:a6d0`
  - generic embedded FT2232H identity `0403:6010`
  - JTAG on FTDI channel A
  - automatic `PWR_RST` latch clearing

- XDS100v3 support:
  - `0403:a6d1`
  - the same GPIO/CPLD protocol as XDS100v2

- Auto-selection config accepting v2, v3, and embedded v2 identities.
- Runtime recovery command after a target-only power cycle.
- Linux udev rules for both branded PIDs.
- Windows and POSIX programmer wrappers.
- A generic OpenOCD programmer configuration.
- Idempotent semantic source patcher with dry-run and check modes.
- Python and Tcl regression tests.

## Apply to xsession/openocd

Linux, macOS, Git Bash, or WSL:

```console
./scripts/apply.sh /path/to/xsession-openocd
```

Windows PowerShell:

```powershell
.\scripts\apply.ps1 -OpenOcdRoot C:\path\to\openocd
```

Inspect the source changes first:

```console
python3 scripts/apply_xds100_support.py /path/to/openocd --dry-run
```

Verify an already-patched checkout:

```console
python3 scripts/apply_xds100_support.py /path/to/openocd --check
```

The patcher creates `src/jtag/drivers/ftdi.c.xds100-backup` before its first
source edit. It installs the interface configurations, documentation, udev
rule, and generic programmer example into the checkout.

## Build

The FTDI adapter driver must be enabled. The existing xsession Docker build
already uses it, but a native build can use:

```console
./bootstrap
./configure --enable-ftdi --enable-internal-jimtcl --disable-werror
make -j"$(nproc)"
```

Run the bundle tests before building OpenOCD:

```console
./tests/run.sh
```

Then run the OpenOCD project's own build and test targets.

## C2000 ready-made configurations

The bundle includes ready-made adapter/target combinations for the custom
C2000 target files already used by the fork:

```text
examples/c2000/tms320f28069-xds100v2.cfg
examples/c2000/tms320f28069-xds100v3.cfg
examples/c2000/tms320f280049-xds100v2.cfg
examples/c2000/tms320f280049-xds100v3.cfg
examples/c2000/tms320f28m35x-xds100v2.cfg
examples/c2000/tms320f28m35x-xds100v3.cfg
```

Run the scan-only probe and JTAG-chain smoke test before programming flash:

```console
./scripts/test-xds100-openocd.sh ./src/openocd v2 \
  target/ti/tms320f28069.cfg
```

Program only after the selected target backend and flash algorithm have passed
the smoke test:

```console
./src/openocd -f examples/c2000/tms320f28069-xds100v2.cfg \
  -c "program build/application.out verify reset exit"
```

## Program with XDS100v2

```console
openocd \
  -f interface/ftdi/xds100v2.cfg \
  -f target/ti/<device>.cfg \
  -c "adapter speed 1000" \
  -c "program firmware.elf verify reset exit"
```

## Program with XDS100v3

```console
openocd \
  -f interface/ftdi/xds100v3.cfg \
  -f target/ti/<device>.cfg \
  -c "adapter speed 1000" \
  -c "program firmware.elf verify reset exit"
```

Generic wrapper:

```console
./scripts/program-xds100.sh \
  /path/to/openocd \
  v2 \
  target/ti/<device>.cfg \
  build/application.elf
```

PowerShell:

```powershell
.\scripts\program-xds100.ps1 `
  -OpenOcd C:\Tools\OpenOCD\bin\openocd.exe `
  -Version v3 `
  -TargetConfig target\ti\<device>.cfg `
  -Image build\application.elf
```

The target configuration and its flash driver determine actual C2000 flash
programming support. This bundle provides the XDS100 JTAG transport and the
probe-specific initialization needed to reach that target reliably.

## Multiple probes

Use the OpenOCD adapter serial selector:

```console
openocd \
  -f interface/ftdi/xds100v2.cfg \
  -c "adapter serial <serial-number>" \
  -f target/ti/<device>.cfg
```

Use version-specific files where possible. `xds100.cfg` also accepts generic
`0403:6010`, so it can match unrelated FT2232H hardware if no serial or USB
location is supplied.

## Target-only power cycle

When the target is power-cycled while OpenOCD remains running, execute this in
the telnet console:

```text
xds100_recover_after_target_power_cycle
```

This pulses `PWR_RST` and re-runs JTAG chain initialization.

## Linux USB permissions

```console
sudo ./scripts/install-xds100-udev.sh
```

Reconnect the probe after reloading rules.

## Windows USB driver

OpenOCD's FTDI backend requires a libusb-compatible driver on the JTAG
interface. XDS100 commonly exposes two FTDI interfaces: channel A for JTAG and
channel B for UART. Change only the JTAG interface when the UART must remain
available, and record the original driver so TI tooling can be restored.

## Validation scope

The included tests verify source transformation, idempotency, Tcl config
loading, v2/v3 USB identities, GPIO layout, automatic latch clearing, and udev
rules. Physical probe validation still requires an XDS100v2 or XDS100v3,
working target configuration, and target board.

## License

Unless a file states otherwise, this bundle is licensed under
GPL-2.0-or-later. See `NOTICE` and `LICENSES/GPL-2.0-or-later.txt`.
