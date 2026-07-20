# Contributing

1. Keep Microchip pack versions pinned in `packs.toml`.
2. Do not manually edit generated SVD files.
3. Put reviewed corrections in `devices/<device>.yaml`.
4. Add a regression test for converter changes.
5. Run `make check` for source changes.
6. After generating vendor files, run `make check-generated` to execute both the structural and Cortex-Debug compatibility validators.
7. Keep all register offsets byte-addressed (`addressUnitBits = 8`); Cortex-Debug uses `baseAddress + addressOffset` as a byte address when reading memory.
8. Include provenance metadata when publishing generated files.
