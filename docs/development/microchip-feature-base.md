# Microchip feature base

The clean-room Microchip tooling imported from `gens/` now lives at:

```text
tools/microchip/open_microchip_tools/
```

This makes the RI4 protocol research, host-side Python tools, simulator helpers,
Renode co-simulation pieces, tests, and source-only VS Code integration part of
the project tree instead of a loose generated artifact.

The native OpenOCD driver remains the canonical runtime implementation:

- `src/target/mchp_ri4_bridge.c`
- `src/target/mchp_ri4_native.c`
- `src/flash/nor/mchp_ri4.c`
- `tcl/programmer/microchip/pickit4-ri4.cfg`
- `tcl/programmer/microchip/icd4-ri4.cfg`

The import intentionally excludes the generated feature base's older
`openocd/overlay/` files. Those files describe an earlier external bridge path;
the in-tree driver talks RI4 USB natively and is already registered with
OpenOCD.

The import also excludes `vendor/` MPLAB pack snapshots, tool firmware images,
and built VS Code packages. If local asset collection is needed for hardware
experiments, keep those generated files under the ignored
`tools/microchip/open_microchip_tools/vendor/` directory and pass the relevant
script catalog path through `MCHP_RI4_SCRIPTS`.

