# Microchip feature organization

The maintained Microchip implementation is intentionally split by ownership:

- Native RI4 and programmer support lives in `src/` and `tcl/`.
- Curated SVD inputs live in `svd/microchip/`.
- The repo-local MDB debug-server wrapper lives in
  `tools/debug-servers/microchip/mdb/`.
- User-facing presets and VS Code examples live in `examples/microchip/` and
  `examples/vscode/microchip-mdb-cortex-debug/`.

There is no required `tools/microchip/` generated import or unresolved external
submodule. Keeping those vendor/runtime assets out of the maintained tree makes
checkout, packaging, and CI deterministic.

The native OpenOCD driver remains the canonical runtime implementation:

- `src/target/mchp_ri4_bridge.c`
- `src/target/mchp_ri4_native.c`
- `src/flash/nor/mchp_ri4.c`
- `tcl/programmer/microchip/pickit4-ri4.cfg`
- `tcl/programmer/microchip/icd4-ri4.cfg`

The native in-tree driver talks RI4 USB directly and is already registered with
OpenOCD. Proprietary MPLAB packs, tool firmware images, extracted MDB runtimes,
and built VS Code packages are not source dependencies; keep any local copies
under the ignored vendor directory owned by the corresponding tool, such as
`tools/debug-servers/microchip/mdb/vendor/`.
