# Contributing

Thank you for improving this OpenOCD fork.

## Before submitting a change

1. Keep OpenOCD implementation changes separate from packaging/documentation changes.
2. Run the relevant native or containerized build.
3. Update tests and documentation when behavior changes.
4. Avoid committing generated files from `artifacts/`, `.build/`, or `docs/_build/`.
5. Keep platform-specific compatibility changes isolated under `build/scripts/`.

For upstream coding conventions and patch guidance, see [`HACKING`](HACKING).
For packaging architecture, see
[`docs/development/build-system.md`](docs/development/build-system.md).
