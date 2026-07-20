# TI tooling

This directory contains project-local Texas Instruments helpers that support the
OpenOCD TI target, adapter, SVD, and serial-programming work.

OpenOCD-side TI probe configs live under `tcl/interface/ti/`. A built OpenOCD
binary can report its compiled-in TI adapter support with `adapter ti list`.

## Contents

- `flash_f28004x_serial.ps1` wraps TI's external C2000Ware
  `serial_flash_programmer.exe` for F28004x SCI boot-format images.
- `xds100v2_detect.ps1` performs a non-destructive XDS100v2 USB/JTAG scan and
  reports whether Windows has the probe bound to a driver OpenOCD can use.
- `xds100v2_ccs_detect.ps1` uses TI CCS `DSLite.exe` with generated `.ccxml`
  files to test likely C2000 MCU targets through the stock TI XDS100v2 driver.
- `c2000_toolchain/` is a curated source-only import of the TI C2000/MSPM0
  generator, debug adapter, CCS bridge, Renode examples, and validation tooling
  from `gens/ti-c2000-toolchain-0.3.0`.

OpenOCD runtime target and adapter support remains in `src/`, `tcl/`, `udev/`,
and `examples/`.
