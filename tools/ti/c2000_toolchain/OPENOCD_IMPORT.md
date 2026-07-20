# OpenOCD import notes

This tree was imported from `gens/ti-c2000-toolchain-0.3.0` so the TI
C2000/MSPM0 tooling has a stable project location.

Included:

- `src/ti_svd/` SVD and launch-configuration generator source.
- `bridge/` CCS Scripting JSON bridge.
- `extension/` source for the `c2000-debug` VS Code extension.
- `devices/`, `patches/`, `examples/`, `docs/`, `reports/`, `scripts/`, and
  tests that explain and validate the tooling.

Excluded:

- Built `.vsix` packages.
- Generated `svd/` output.
- The nested `openocd/` XDS100 overlay, because this repository already carries
  those OpenOCD runtime files in `src/`, `tcl/`, `udev/`, `docs/usage/`, and
  `examples/c2000/`.
- Per-tool Docker and CI scaffolding; this repository keeps shared Docker
  packaging under top-level `docker/`.

Generated TI SVD output, local CCS extracts, virtual environments, Node
dependencies, and VS Code build output should stay ignored.

