# Overview

OpenOCD provides a bridge between a debugger and embedded hardware. It supports JTAG and SWD adapters, exposes a GDB server, and loads Tcl configuration files describing the adapter, transport, target, and board.

This fork adds a binary deployment layer around the OpenOCD source tree:

- Linux x86-64 package built in Alpine Linux.
- Optional Linux ARM64 package built through Buildx/QEMU or on an ARM64 runner.
- Windows x86-64 package cross-compiled with MinGW-w64.
- macOS x86-64 and ARM64 packages built natively.
- GitHub Actions release workflow for repeatable artifacts.

## Documentation architecture

The repository keeps two documentation systems for different jobs:

- `docs/`: Sphinx/MyST site for installation, packaging, CI, and task-oriented guides.
- `doc/openocd.texi`: upstream OpenOCD command and protocol reference.
- `Doxyfile.in`: source-code API documentation for maintainers.

The Sphinx site links to the legacy manual instead of duplicating thousands of command descriptions.
