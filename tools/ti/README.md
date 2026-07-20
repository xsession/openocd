# TI tooling

This directory contains project-local Texas Instruments helpers that support the
OpenOCD TI target, adapter, SVD, and serial-programming work.

## Contents

- `flash_f28004x_serial.ps1` wraps TI's external C2000Ware
  `serial_flash_programmer.exe` for F28004x SCI boot-format images.
- `c2000_toolchain/` is a curated source-only import of the TI C2000/MSPM0
  generator, debug adapter, CCS bridge, Renode examples, and validation tooling
  from `gens/ti-c2000-toolchain-0.3.0`.

OpenOCD runtime target and adapter support remains in `src/`, `tcl/`, `udev/`,
and `examples/`.

