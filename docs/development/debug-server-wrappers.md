# Debug-server wrappers

The repository-local wrappers are maintained under `tools/debug-servers/` and
are kept separate from OpenOCD's compiled runtime:

- `tools/debug-servers/microchip/mdb/` provides the Microchip MDB GDB/RSP
  facade.
- `tools/debug-servers/ti/c2000/` provides the TI C2000 OpenOCD wrapper and
  monitor-only GDB proxy.

Use the vendor README next to each wrapper for prerequisites, commands, ports,
and hardware-validation limits. These wrappers may call external vendor tools;
they do not replace the canonical `src/` and `tcl/` OpenOCD implementation.
