# Source catalog

This project keeps generated feature drops in `gens/` only as import staging.
Maintained source belongs in the categorized project tree below.

## Runtime source

| Path | Purpose |
|---|---|
| `src/` | OpenOCD C implementation, target drivers, flash drivers, adapter drivers, server code, and helper libraries. |
| `tcl/` | Runtime OpenOCD scripts installed as package data: interfaces, targets, boards, programmers, and helpers. |
| `udev/` | Linux USB permission rules for supported adapters and probes. |
| `contrib/` | Upstream-style auxiliary utilities and examples. |
| `jimtcl/` | Vendored Jim Tcl submodule/source used by OpenOCD builds. |

## Project feature tooling

| Path | Purpose |
|---|---|
| `tools/ti/` | TI C2000/MSPM0 generators, debug helpers, CCS bridge, Renode examples, and serial flashing helper. |
| `tools/microchip/` | Microchip RI4, IPECMD, MDBCore, Renode co-simulation, simulator, and VS Code helper tooling. |
| `tools/release/`, `tools/scripts/`, and legacy tool files | Existing OpenOCD maintenance and release utilities. |

## Data and examples

| Path | Purpose |
|---|---|
| `svd/` | Curated debugger-facing SVD files committed with the fork. Generator source lives under `tools/`. |
| `examples/` | Ready-to-run board, target, adapter, and programming examples. |
| `testing/` | OpenOCD test infrastructure and regression scripts. |

## Documentation and packaging

| Path | Purpose |
|---|---|
| `doc/` | Upstream Texinfo/manual source. |
| `docs/` | Fork-specific Markdown documentation, feature notes, and development records. |
| `docker/` | Dockerfiles, Compose/Bake files, packaging scripts, and Docker runtime data. |
| `.github/` | CI and repository automation. |

## Staging and generated output

| Path | Purpose |
|---|---|
| `gens/` | Ignored generated/source-drop staging area. Review and curate from here; do not make runtime code depend on it. |
| `artifacts/` | Ignored package/build outputs. |
| `dist/`, `build-*`, `.venv`, `node_modules`, `__pycache__` | Local build or tool output. |

## Import rule

When a feature from `gens/` is promoted into the project:

1. Copy only source, docs, tests, and small deterministic config.
2. Exclude generated binaries, firmware blobs, packed extensions, extracted
   vendor databases, and duplicate OpenOCD snapshots.
3. Add a short `OPENOCD_IMPORT.md` in the imported feature directory.
4. Register the maintained destination in docs and distribution metadata.

