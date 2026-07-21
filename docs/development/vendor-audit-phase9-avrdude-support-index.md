# Vendor Audit Phase 9: AVRDUDE And Support Index

Phase 9 closes the audit queue by adding a delegated AVRDUDE programming lane
and a Zephyr-style support metadata layer.

## Scope

| Area | Decision |
| --- | --- |
| AVRDUDE support | Integrated as an external command bridge. |
| MCU/programmer catalog | Delegated to the installed `avrdude` executable and its `avrdude.conf`. |
| Native AVR protocol backends | Deferred to protocol-specific C backend batches. |
| Repository organization | Added `support/` metadata roots inspired by Zephyr's board, SoC, module, and vendor layout. |
| OpenOCD runtime paths | Left unchanged under `tcl/`, `src/`, `contrib/`, and `docs/`. |

## Files Added

| File or directory | Purpose |
| --- | --- |
| `tcl/programmer/avrdude/common.tcl` | OpenOCD Tcl command bridge to external AVRDUDE. |
| `docs/programmers/avrdude.md` | Beginner-facing AVRDUDE bridge usage docs. |
| `docs/development/avrdude-integration-audit.md` | AVRDUDE source pin, inventory, and native-port queue. |
| `docs/development/zephyr-style-support-organization.md` | Explanation of the new `support/` metadata layout. |
| `support/` | Zephyr-style board, SoC, programmer, module, and vendor metadata. |

## AVRDUDE Inventory

| Field | Value |
| --- | --- |
| Source | `https://github.com/avrdudes/avrdude.git` |
| Audited commit | `7154723b9efa8bad989b2b339c303aa9d12014e2` |
| Latest checked tag | `v8.2` at `65dd419fdde8a018f718a07351c674121edba2cd` |
| Part blocks | 406 |
| Programmer blocks | 174 |
| Integration mode | Delegated external executable |

## Support Index Coverage

| Metadata family | Entries added |
| --- | ---: |
| Vendors | 2 |
| Modules | 1 |
| SoCs | 3 |
| Boards | 6 |
| Programmers | 4 |

Indexed support includes:

- TI C2000 SoCs: `tms320f280049`, `tms320f28069`, and `tms320f28m35x`.
- TI XDS100 board pairings for all six C2000 board files added in Phase 6.
- TI programmers: XDS100v2, XDS100v3, and XDS110.
- AVRDUDE delegated external programmer bridge.

## Validation

AVRDUDE bridge help loaded with the source-tree scripts:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f programmer/avrdude/common.tcl `
  -c "avrdude help" `
  -c shutdown
```

AVRDUDE dry-run command construction passed:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f programmer/avrdude/common.tcl `
  -c "avrdude dry_run on" `
  -c "avrdude programmer arduino" `
  -c "avrdude part atmega328p" `
  -c "avrdude port COM1" `
  -c "avrdude baud 115200" `
  -c "avrdude program docs/index.md" `
  -c shutdown
```

The packaged script tree was refreshed and validated:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f programmer/avrdude/common.tcl `
  -c "avrdude dry_run on" `
  -c "avrdude programmer usbasp" `
  -c "avrdude part atmega328p" `
  -c "avrdude command read flash flash.hex i" `
  -c shutdown
```

Support metadata references were checked so every referenced `tcl/`, `docs/`,
`examples/`, and `tools/` path exists.

## Result

Phase 9 is complete. The tree now has broad delegated AVRDUDE programming
access, documented native-port boundaries, and a Zephyr-style support index
without breaking OpenOCD runtime packaging conventions.
