# Debug Server Wrappers

This folder groups repo-local debug-server wrappers and their dependency
manifests by vendor.

| Folder | Purpose |
| --- | --- |
| `microchip/mdb/` | GDB/RSP facade backed by Microchip MPLAB X MDB command files. |
| `ti/c2000/` | OpenOCD wrapper and monitor-only GDB proxy for TI C2000/F28M35x bring-up. |

The paths under this directory are the canonical entry points. Do not add
duplicate compatibility launchers at the repository root; update the relevant
vendor wrapper and its README when the command-line interface changes.
