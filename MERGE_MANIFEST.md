# Unified OpenOCD merge manifest

This source tree uses the previously produced TMS320-family OpenOCD source as
its base and layers the Microchip programmer integration onto it.

## Base retained

- Cross-platform Docker and native packaging.
- Documentation refactor and VS Code support files.
- TI C2000/C28x custom target integration.
- TMS320 generated family configuration database.
- TMS320F28M35x, TMS320F28069, and TMS320F280049 presets.
- XDS100v2 and XDS100v3 FTDI configurations and udev identifiers.
- XDS110 integration already present in the fork.
- MSPM0C1103 target, board, flash, and documentation support.

## Added layer

- PICkit 2, PICkit 3, PICkit 4, and MPLAB ICD 4 programmer presets.
- Shared `microchip` Tcl command implementation.
- MPLAB IPECMD, `pk2cmd`, and explicitly selected `pymcuprog` command builders.
- PICkit 4 and ICD 4 CMSIS-DAP interface configurations.
- Linux udev rules for the Microchip probes.
- Ten automated programmer integration tests.
- CI workflow and programming documentation.

## Merge policy

- The TMS320-family tree is authoritative for files not touched by the
  Microchip integration.
- The Microchip integration changes only additive files plus the shared
  distribution manifests, README, test manifest, and udev rules.
- Generated Autotools outputs are excluded from the final repository archive;
  run `./bootstrap` after checkout.
- No proprietary Microchip programming scripts or device databases are
  included.

## Expected key files

```text
src/target/c28x.c
src/target/c28x.h
tcl/interface/ftdi/xds100v2.cfg
tcl/interface/ftdi/xds100v3.cfg
tcl/target/ti/tms320f28m35x.cfg
tcl/target/ti/tms320f28069.cfg
tcl/target/ti/tms320f280049.cfg
tcl/target/ti/mspm0c1103.cfg
tcl/programmer/microchip/common.tcl
tcl/programmer/microchip/pickit2.cfg
tcl/programmer/microchip/pickit3.cfg
tcl/programmer/microchip/pickit4.cfg
tcl/programmer/microchip/icd4.cfg
tcl/interface/microchip/pickit4-cmsis-dap.cfg
tcl/interface/microchip/icd4-cmsis-dap.cfg
```
