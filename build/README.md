# Build and packaging infrastructure

This directory contains repository-owned build infrastructure. It is separate from
OpenOCD source code so packaging changes do not obscure upstream components.

## Layout

- `containers/` — reproducible Linux, Windows cross-build, and documentation images.
- `scripts/` — stable developer and CI entry points.

Generated packages are written to the root-level `artifacts/` directory and are
not committed.

## Common commands

```console
docker compose up --build
docker buildx bake all
./build/scripts/build-linux-package.sh
./build/scripts/build-windows-cross.sh
./build/scripts/build-macos-package.sh
./build/scripts/build-docs.sh
```
