# Vendor Audit Phase 10: Backend And Hardware Queue

Phase 10 closes the remaining audit queue by separating locally actionable work
from work that needs real hardware or full C backend imports. No Tcl-only files
were imported in this phase because the remaining candidates depend on target,
transport, adapter, or flash backend code.

## Scope

| Queue item | Phase 10 decision |
| --- | --- |
| TI C2000 hardware path | Keep integrated docs/config/package support; real attach remains a hardware gate. |
| Espressif newer chips | Defer to a full Espressif target and flash backend batch. |
| WCH CH32/WCH-Link | Defer to a full adapter, transport, target, and flash backend batch. |
| Nuvoton M23/M23_NS | Defer until `numicro.c` flash-region handling is reviewed and imported. |
| Zephyr SDK `rv32m1`/`nds32` | Defer until target backend ownership is decided. |
| RISC-V collaboration | Defer core behavior changes until hardware or simulator validation is available. |
| Arduino OpenOCD | Defer old NDS32/package-flow files unless NDS32 is restored. |
| Microchip, ST, Nordic, NXP, Silicon Labs, GigaDevice, Raspberry Pi | Leave covered by local support unless a newer self-contained file appears. |

## Metadata Added

The queue is now represented under the Zephyr-style support metadata tree:

| Metadata file | Status |
| --- | --- |
| `support/modules/ti-hardware-validation/module.yml` | blocked |
| `support/modules/espressif-backend/module.yml` | deferred |
| `support/modules/wch-backend/module.yml` | deferred |
| `support/modules/nuvoton-backend/module.yml` | deferred |
| `support/modules/zephyr-sdk-targets/module.yml` | deferred |
| `support/modules/riscv-collaboration/module.yml` | deferred |
| `support/modules/arduino-openocd/module.yml` | deferred |

## Acceptance Gates

| Queue item | Required before integration |
| --- | --- |
| TI C2000 hardware path | Real XDS100v2/v3 or XDS110 probe, powered recoverable C2000 hardware, `scan_chain`, `targets`, halt/resume/step/register/memory checks. |
| TI C2000 flash | Successful real attach, safe RAM work area, flash probe, erase/write/verify/protect tests on recoverable hardware. |
| Espressif | Import matching `src/target/espressif` and flash helpers, then run native build, Windows package build, and dummy-config tests for every new target script. |
| WCH | Import WCH adapter/transport/target/flash code together; validate with CH32 hardware or a documented simulator boundary. |
| Nuvoton | Review and import the newer `numicro.c` flash-region implementation before adding M23/M23_NS aliases. |
| Zephyr SDK | Decide whether `rv32m1` and `nds32` target backends belong in this fork; do not import board files alone. |
| RISC-V collaboration | Review as a core target backend change with broad regression coverage. |
| Arduino OpenOCD | Restore NDS32 only as a deliberate backend decision; otherwise leave package-flow files out. |

## Local Validation

Phase 10 did not add runtime Tcl or C backends. It rechecked the existing
metadata and script surfaces that the queue depends on:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c shutdown

.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
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

Phase 10 is complete as a queue-closure phase. The remaining work is not
config-only and should start as Phase 12 backend or hardware implementation
batches with explicit hardware, simulator, build, and regression gates.
