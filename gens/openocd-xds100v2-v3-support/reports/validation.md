# XDS100v2/v3 support validation

Date: 2026-07-17

## Implemented

- Current OpenOCD FTDI command syntax and USB selection.
- XDS100v2 IDs `0403:a6d0` and compatible embedded `0403:6010`.
- XDS100v3 ID `0403:a6d1`.
- FTDI channel A/JTAG GPIO layout.
- New `ftdi initial_signal` configuration command.
- A physically committed low state followed by a pre-scan `PWR_RST` high state.
- Runtime target-power-cycle recovery procedure.
- Linux udev rules, Windows/POSIX wrappers, and six C2000 examples.

## Automated results

- Python semantic-installer tests: **5 passed**.
- Tcl interface/configuration suite: **passed**.
- Static bundle validation: **passed**.
- POSIX shell syntax checks: **passed**.
- Python bytecode compilation: **passed**.
- Standalone patch `git apply --check` against the current-shaped FTDI fixture: **passed**.
- Patched FTDI fixture compiled with GCC using GNU C11, warnings enabled: **passed**.

The tests cover:

- current and legacy OpenOCD FTDI cleanup layouts;
- source transformation, backup creation, dry-run and `--check` modes;
- idempotent reapplication;
- v2, v3 and auto USB identities;
- FTDI channel A, JTAG transport and GPIO layout;
- the initial `PWR_RST` latch-clearing transition;
- runtime low/high pulse and `jtag arp_init` recovery sequence;
- udev rules and installation of all C2000 example combinations.

## Hardware boundary

No physical XDS100v2/XDS100v3 and C2000 board were connected in this
environment. The package validates the OpenOCD probe transport and
initialization implementation offline. It does **not** claim that the custom
C28x halt/register/memory/flash backend has been qualified on hardware. Run the
included scan-only script first, and do not issue an erase/program command until
target examination and flash-bank reporting succeed on the selected board.
