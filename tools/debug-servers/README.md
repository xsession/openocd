# Debug Server Wrappers

This folder groups repo-local debug-server wrappers and their dependency
manifests by vendor.

| Folder | Purpose |
| --- | --- |
| `microchip/mdb/` | GDB/RSP facade backed by Microchip MPLAB X MDB command files. |
| `ti/c2000/` | OpenOCD wrapper and monitor-only GDB proxy for TI C2000/F28M35x bring-up. |

The wrappers in `tools/support/` remain as compatibility launchers. New docs and
examples should point here.
