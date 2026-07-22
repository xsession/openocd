# OpenOCD Examples

This folder contains small example config files that show how to start OpenOCD
for common adapters and target combinations.

These files are not a replacement for the full configs under `tcl/`. They are
copy-paste friendly starting points for testing a probe, attaching to a target,
or programming firmware.

## Basic Command Shape

Run examples from the repository root:

```console
openocd -s ./tcl -f examples/<example>.cfg
```

If you are using a built Windows package, replace `openocd` with the full path
to the packaged executable:

```console
artifacts/windows/openocd-windows-x86_64/bin/openocd.exe -s ./tcl -f examples/<example>.cfg
```

The `-s ./tcl` option tells OpenOCD where to find the standard scripts used by
the example files.

## What Each Example Does

| File | Use it for |
| --- | --- |
| `cmsis-dap-swd.cfg` | A minimal CMSIS-DAP probe using SWD. |
| `ftdi-jtag.cfg` | A minimal FTDI-style JTAG setup. |
| `stlink-stm32f4.cfg` | A simple ST-Link plus STM32F4 example. |
| `program-xds100.cfg` | A reusable TI XDS100 wrapper for programming a selected target. |
| `c2000/*.cfg` | TI C2000 examples using XDS100v2 or XDS100v3 probes. |
| `vscode/f28m35x-cortex-debug/` | VS Code tasks and launch templates for F28M35x dual-core bring-up. |

## First Test: Start And Exit

Before trying to halt or flash a chip, check that OpenOCD can load the config:

```console
openocd -s ./tcl -f examples/cmsis-dap-swd.cfg -c "init; shutdown"
```

For a board-specific example:

```console
openocd -s ./tcl -f examples/c2000/tms320f28069-xds100v3.cfg -c "init; scan_chain; shutdown"
```

If this fails, fix the probe driver, cable, target power, boot mode, or config
selection before trying flash commands.

## Programming With XDS100

`program-xds100.cfg` is a wrapper. You choose the XDS100 interface and the
target config from the command line.

Example for XDS100v3 and a TI F28M35x target:

```console
openocd -s ./tcl \
  -c "set XDS100_INTERFACE interface/ti/xds100v3.cfg" \
  -c "set TARGET_CONFIG target/ti/tms320f28m35x.cfg" \
  -f examples/program-xds100.cfg \
  -c "program firmware.elf verify reset exit"
```

Example for XDS100v2 and a TI F28069 target:

```console
openocd -s ./tcl \
  -c "set XDS100_INTERFACE interface/ti/xds100v2.cfg" \
  -c "set TARGET_CONFIG target/ti/tms320f28069.cfg" \
  -f examples/program-xds100.cfg \
  -c "program firmware.elf verify reset exit"
```

Replace `firmware.elf` with your real firmware file.

## VS Code F28M35x Bring-Up

The `examples/vscode/f28m35x-cortex-debug/` folder contains beginner-friendly
VS Code files for the F28M35x plus XDS100v3 workflow:

- run OpenOCD preflight checks,
- run ICEPick discovery,
- start one shared OpenOCD server,
- monitor the validated C28x target, and
- stage the intended Cortex-M3 plus C28x compound launch.

The C28x monitor flow works with the OpenOCD TCL monitor. Full simultaneous
source debugging still requires OpenOCD to expose the Cortex-M3 target and a
C28x-capable GDB/debug backend for the C28x target.

## Common Options

Set adapter speed:

```console
openocd -s ./tcl \
  -c "set XDS100_ADAPTER_SPEED 500" \
  -c "set TARGET_CONFIG target/ti/tms320f28069.cfg" \
  -f examples/program-xds100.cfg \
  -c "init; shutdown"
```

Select a probe by serial number when more than one probe is connected:

```console
openocd -s ./tcl -f examples/c2000/tms320f28069-xds100v3.cfg \
  -c "adapter serial <serial-number>" \
  -c "init; scan_chain; shutdown"
```

Start OpenOCD for GDB:

```console
openocd -s ./tcl -f examples/c2000/tms320f28069-xds100v3.cfg
```

Then connect GDB to the port printed by OpenOCD, usually `3333`.

## When To Use `tcl/board` Instead

Prefer a board file under `tcl/board/` when one exists for your exact hardware.
Board files usually know the right adapter, target, reset behavior, and default
speed for a real development board.

Use `examples/` when:

- you are learning how configs fit together,
- you are testing a new adapter and target combination,
- you need a short command for a known target,
- you are writing a new config and want a simple starting point.

## Safety Notes

- Start with `init; scan_chain; shutdown` before programming.
- Use a low adapter speed, such as `100` or `500`, on new hardware.
- Do not run flash commands until target attach and memory reads work.
- Check that the target board is powered and not held in reset.
- On Windows, some USB probes need WinUSB or another libusb-compatible driver
  on the debug interface.

## Adding A New Example

When adding an example:

1. Keep it short.
2. Use `source [find ...]` instead of absolute paths.
3. Set a conservative adapter speed.
4. Avoid destructive commands such as erase or program inside the example file.
5. Add a comment at the top saying what hardware it targets.
6. Update this README.
