# OpenOCD import notes

This tree was imported from the generated `open_microchip_tools` feature base
under `gens/` so the clean-room Microchip RI4 tooling lives in a stable project
location.

Included:

- Python packages for RI4, IPECMD, MDBCore, GDB/RSP, Renode co-simulation,
  simulator helpers, VS Code backend helpers, and Zephyr replacement research.
- Source-only VS Code extension files.
- Documentation, tests, and packaging metadata from the feature base.

Excluded:

- `vendor/` MPLAB assets and firmware snapshots.
- The older `openocd/overlay/` integration, because this repository already has
  the maintained native C implementation wired into OpenOCD.
- Built VS Code extension output and `.vsix` packages.

Generated or collected Microchip pack assets should stay local and ignored.
Use explicit `MCHP_RI4_SCRIPTS` paths when running OpenOCD against MPLAB script
catalogs.

