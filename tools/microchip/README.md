# Microchip tooling

This directory contains project-local Microchip helper tooling that supports the
native PICkit 4 / ICD 4 RI4 target implementation in OpenOCD.

## Contents

- `open_microchip_tools/` is a curated import of the clean-room protocol and
  simulator feature base from `gens/open_microchip_tools-dspic30-renode-openocd-source(1)`.

The native OpenOCD implementation remains in `src/target/mchp_ri4_*`,
`src/flash/nor/mchp_ri4.c`, and `tcl/programmer/microchip/*-ri4.cfg`.

