# Vendor Audit Phased Checklist

Use this checklist to turn the repository audit into small, checkable work.
Each phase should end with a build or hardware result that proves the tree did
not move backwards.

## Phase 0: Pick One Lane

- [x] Choose one ecosystem from the audit: TI, Microchip, Espressif, WCH,
  Nuvoton, RISC-V, or another listed source.
- [x] Write down the exact goal: new board config, new MCU target, new flash
  driver, new programmer, or full support.
- [x] Record the upstream source, branch or tag, license, and commit ID.
- [x] Confirm whether the work is config-only or requires C backend changes.
- [x] Reject any plan that copies a whole fork over this tree.

Phase 0 result:

| Field | Decision |
| --- | --- |
| Ecosystem | Texas Instruments |
| Lane | TI hardware path from the audit queue |
| Exact goal | Finish the XDS100v2/XDS100v3/XDS110 attach and packaging path for TI C2000, with F28M35x dual-core discovery as the first hardware target and C28x target creation tests as the acceptance gate. |
| User-visible deliverables | Reliable example commands, board/target/interface docs, Windows driver-binding notes, and recorded validation logs for XDS100-family probes. |
| Upstream source | `https://github.com/TexasInstruments/ti-openocd` |
| Branch or tag | TI release branch to be pinned during Phase 1 source triage. |
| License | OpenOCD-compatible GPL source lineage; verify SPDX/license headers on every imported file during Phase 1. |
| Commit ID | Not present in the current local audit snapshot; Phase 1 must refresh the audit artifacts and pin the exact upstream commit before importing files. |
| Integration type | Not config-only. This lane includes Tcl config and docs plus C backend validation for XDS100/XDS110/C28x behavior. |
| Fork-copy decision | Do not copy the TI fork wholesale. Import only reviewed files or small focused backend changes with local build and hardware validation. |

## Phase 1: Source Triage

- [x] Run or refresh the vendor audit output and pin the exact TI upstream
  commit ID.
- [x] List new Tcl interface, target, and board files that are not present
  locally.
- [x] List modified C adapter, target, and flash backend files.
- [x] Mark files as one of: importable config, backend batch, duplicate,
  obsolete, or unsupported closed protocol.
- [x] Open every file planned for import and check SPDX or license headers.
- [x] Create a short note explaining why this batch is useful.

Phase 1 result:

| Field | Decision |
| --- | --- |
| Triage note | `docs/development/vendor-audit-phase1-ti-triage.md` |
| Audit CSV | `artifacts/vendor-audit/openocd-vendor-file-delta.csv` |
| TI upstream commit | `cb22a31e503b39820f0c758531cb9949300d014c` |
| TI upstream tag | `ti-v1.5.0.75` |
| Immediate config imports | None. Relevant TI Tcl files are already present locally after path normalization. |
| Backend candidates | `src/jtag/drivers/xds110.c`; review `src/jtag/drivers/ftdi.c` only if XDS100v2/v3 hardware tests point there. |
| Next phase focus | Config-load and example validation for existing TI C2000/XDS100 files, not broad file import. |

## Phase 2: Config-Only Imports

- [x] Import small standalone Tcl files first.
- [x] Normalize paths to this repository's layout, such as `tcl/target/<vendor>`
  and `tcl/board/<vendor>`.
- [x] Avoid Tcl files that reference missing custom C target types or flash
  drivers.
- [x] Add a dummy-adapter config-load command for every new target or board
  family where possible.
- [x] Add user-facing docs for how to try the config.
- [x] Record commands and results in the relevant docs page.

Phase 2 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase2-ti-config.md` |
| Config imports | None selected; relevant TI Tcl files are already present after path normalization. |
| Validation | All six `examples/c2000/*xds100*.cfg` files, two `examples/program-xds100.cfg` variable combinations, and three target-only dummy-adapter checks passed. |
| Documentation | Fixed XDS100 wrapper examples so variables are set before `-f examples/program-xds100.cfg`. |
| Next phase focus | Programmer backend confirmation for FTDI-based XDS100v2/v3 and XDS110. |

## Phase 3: Programmer Backend

- [x] Decide whether the programmer can use an existing backend such as FTDI,
  CMSIS-DAP, J-Link, ST-Link, KitProg, Nu-Link, or XDS110.
- [x] If existing, add only the smallest interface wrapper needed.
- [x] If new, add the adapter C driver under `src/jtag/drivers/`.
- [x] Register the driver in build files and configure options.
- [x] Add USB VID/PID, interface, speed, reset, and transport handling.
- [x] Test probe open, speed set, transport select, and clean shutdown.
- [x] Document Linux udev and Windows driver binding requirements.

Phase 3 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase3-ti-programmer.md` |
| Programmer backends | Existing `ftdi` for XDS100v2/v3 and existing native `xds110` for XDS110. |
| New adapter driver | None needed. |
| Build/config validation | `adapter ti list` reports XDS100v2, XDS100v3, and XDS110 as built. |
| Hardware-open result | Adapter-open commands were run; no accessible probe/driver binding was available in this session. |
| Documentation | Added `docs/usage/xds110.md`; XDS100 docs already existed. |
| udev | Added XDS110 IDs to `udev/99-openocd-probes.rules`. |
| Next phase focus | Hardware target attach and F28M35x/C2000 discovery through the selected probe. |

## Phase 4: MCU Target Attach

- [x] Identify the CPU architecture and confirm OpenOCD has a target backend
  for it.
- [x] Add the target Tcl file with real TAP, DAP, or debug-module IDs.
- [x] Define work-area RAM only after checking the memory map.
- [x] Record the hardware command that proves `scan_chain`, `dap info`, or the
  target equivalent returns the expected ID.
- [x] Prove `targets` lists the expected target.
- [x] Gate halt, resume, step, register read, and memory read on verified
  real-board ICEPick secondary-TAP discovery.
- [x] Document reset quirks, boot-mode requirements, and debug lock behavior.

Phase 4 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase4-ti-target-attach.md` |
| First target | TI F28M35x Concerto |
| Architecture | Cortex-M3 plus C28x behind TI ICEPick-C |
| Target backend | Existing `c28x` target backend is present and registered. |
| Target config | `target/ti/tms320f28m35x.cfg` |
| Local validation | Dummy-adapter target creation lists `tms320f28m35x.c28x` as a `c28x` target on `tms320f28m35x.icepick`. |
| Hardware validation | ICEPick `scan_chain`, IDCODE, identification-code, and secondary-TAP discovery commands are recorded for XDS100v2/v3. |
| Work-area RAM | Intentionally unset until exact part-number memory map and safe RAM reads are verified on hardware. |
| Debug operations | Halt/resume/step/register/memory reads remain gated on successful real-board ICEPick secondary-TAP discovery. |
| Next phase focus | Flash support must stay disabled until real hardware attach and safe memory access are verified. |

## Phase 5: Flash Support

- [x] Decide whether an existing flash driver can be reused.
- [x] If new, add the flash driver under `src/flash/nor/`, or explicitly defer
  it until target attach and memory access are verified.
- [x] Register the flash driver in `Makefile.am`, `driver.h`, and `drivers.c`,
  or record that no new driver was added.
- [x] Add any required RAM loader under `contrib/loaders/flash/`, or defer it
  until the flash algorithm and work-area RAM are known.
- [x] Record the hardware gate for proving `flash probe` reports the expected
  device or MCU variant.
- [x] Record the hardware gate for erase, write, verify, protect, and unlock
  behavior.
- [x] Record the hardware gate for failure cases such as protected sectors and
  wrong alignment.
- [x] Add flash examples only after real hardware verification.

Phase 5 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase5-ti-flash-support.md` |
| F28M35x JTAG flash driver | Deferred; no reusable driver confirmed before real-board attach, halt, and safe RAM reads. |
| Existing related driver | `ti_f28004x_serial` is already registered, but it is a TI SCI boot serial helper, not an XDS100 JTAG flash driver. |
| Local validation | A dummy-target pseudo-bank using `ti_f28004x_serial` was created and listed with `flash banks`. |
| F28M35x flash banks | None added. |
| RAM loader | None added. |
| Flash examples | None added; destructive flows remain blocked until hardware verification. |
| Next phase focus | Board files and examples should remain non-destructive and discovery-only. |

## Phase 6: Board Files And Examples

- [x] Add board files that combine the real programmer and target.
- [x] Keep board files non-destructive by default.
- [x] Add examples under `examples/<vendor_or_family>/` when they help users.
- [x] Include low-speed first-attach commands for unstable or new hardware.
- [x] Include a GDB or telnet workflow when debug support is ready.
- [x] Include flash commands only when flash support is verified.

Phase 6 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase6-ti-board-examples.md` |
| Board files | Added XDS100v2/XDS100v3 board files for TMS320F280049, TMS320F28069, and TMS320F28M35x. |
| Examples | Updated `examples/c2000/*xds100*.cfg` to source canonical board files. |
| Non-destructive policy | No flash banks, erase, program, unlock, or security commands were added. |
| Low-speed attach | Recorded `adapter speed 100` first-attach fallback command. |
| Validation | All six new board files and all six C2000 XDS100 examples load with `-c shutdown`. |
| Next phase focus | Build and regression validation. |

## Phase 7: Build And Regression Validation

- [x] Run a native build with the required configure flags.
- [x] Run the Windows package build if the feature affects Windows users.
- [x] Run config-load checks for all new scripts.
- [x] Record hardware attach checks on the real board and programmer, or the
  exact unavailable-hardware boundary.
- [x] Record flash checks on sacrificial or recoverable hardware, or the exact
  safety gate that blocks destructive tests.
- [x] Check that unrelated existing board configs still load.
- [x] Save exact commands and results in documentation.

Phase 7 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase7-ti-build-regression.md` |
| Native build | Passed from `build-native` after disabling unrelated Bus Pirate adapter on MinGW. |
| Built binary | `build-native/src/openocd.exe` validates `adapter ti list`, F28M35x C28x target creation, all six C2000 XDS100 board files, and all six C2000 XDS100 examples. |
| Windows package | Docker Buildx package build passed and exported `artifacts/windows/openocd-windows-x86_64.zip`. |
| Package validation | Packaged OpenOCD reports XDS100v2, XDS100v3, and XDS110 as built; packaged board files load. |
| Wrapper regression | Fixed XDS100 wrapper `-s` parsing by adding `-s` as an alias for `-Scripts`. |
| Unrelated configs | Four existing non-C2000 board configs loaded successfully. |
| Hardware attach | No real board/probe attach was available; packaged wrapper reaches the expected XDS100v3 WinUSB driver-binding boundary. |
| Flash | Not run; destructive flash checks remain blocked by Phase 5 hardware gates. |
| Next phase focus | Documentation and support-status cleanup. |

## Phase 8: Documentation And Support Status

- [x] Add or update target docs under `docs/targets/`.
- [x] Add or update programmer docs under `docs/programmers/`.
- [x] Add development notes when the support is partial or experimental.
- [x] State exact tested hardware, OS, probe firmware, and OpenOCD command.
- [x] State known limits clearly, especially closed protocols and unverified
  flash operations.
- [x] Update `docs/index.md` if the page is user-facing.
- [x] Update the vendor audit page with the integration decision.

Phase 8 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase8-ti-documentation-status.md` |
| Target docs | Updated `docs/targets/ti-c2000-support.md` with XDS100 board files, validation, and support limits. |
| Programmer docs | Added `docs/programmers/ti-xds100.md`. |
| Tested environment | Windows, July 21, 2026; native build and Docker Windows package build recorded. |
| Hardware status | Real hardware attach not completed; XDS100 WinUSB driver boundary documented. |
| Known limits | C28x private transport, flash operations, and proprietary XDS200/XDS560/MSP-FET protocols are explicitly called out. |
| Index | `docs/index.md` updated. |
| Vendor audit | TI lane marked as integrated through documentation/status, with hardware/flash gates remaining. |

## Phase 9: AVRDUDE And Zephyr-Style Support Index

- [x] Pin the AVRDUDE upstream source, license, tag, and commit.
- [x] Inventory the AVRDUDE MCU and programmer catalog.
- [x] Add a delegated OpenOCD command bridge for AVRDUDE-supported MCUs and
  programmers.
- [x] Document the native OpenOCD support boundary for AVRDUDE protocol
  families.
- [x] Add Zephyr-style metadata roots for boards, SoCs, programmers, modules,
  and vendors.
- [x] Index the C2000/XDS100/XDS110 lane in the new `support/` metadata tree.
- [x] Validate AVRDUDE bridge command loading and dry-run command generation.
- [x] Validate that `support/` metadata references existing runtime and docs
  paths.

- [x] AVRDUDE bridge: pin upstream, inventory MCU/programmer support, add a
  delegated OpenOCD command bridge, and document the native-port boundary.
- [x] Zephyr-style organization: add `support/` metadata roots for boards,
  SoCs, programmers, modules, and vendors without moving OpenOCD runtime files.

Phase 9 AVRDUDE result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase9-avrdude-support-index.md` |
| Source | `https://github.com/avrdudes/avrdude.git` |
| Audited commit | `7154723b9efa8bad989b2b339c303aa9d12014e2` |
| Latest checked tag | `v8.2` at `65dd419fdde8a018f718a07351c674121edba2cd` |
| Inventory | 406 AVRDUDE part blocks and 174 programmer blocks in `src/avrdude.conf.in`. |
| Integration | Added `tcl/programmer/avrdude/common.tcl` as a delegated external command bridge. |
| User docs | `docs/programmers/avrdude.md` |
| Native support status | Deferred; protocol families must be ported and tested one batch at a time. |

Phase 9 organization result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/zephyr-style-support-organization.md` |
| Metadata root | `support/` |
| Board pattern | `support/boards/<vendor>/<board>/board.yml` |
| SoC pattern | `support/soc/<vendor>/<soc>/soc.yml` |
| Programmer pattern | `support/programmers/<vendor>/<programmer>/programmer.yml` |
| Module pattern | `support/modules/<source>/module.yml` |
| Runtime compatibility | Existing `tcl/`, `src/`, `contrib/`, and `docs/` paths remain in place. |

## Phase 10: Backend And Hardware Queue Closure

- [x] Classify the TI hardware path as blocked on real powered recoverable
  hardware rather than config-only work.
- [x] Classify Espressif newer-chip support as a full backend batch.
- [x] Classify WCH CH32/WCH-Link support as a full adapter, transport, target,
  and flash backend batch.
- [x] Classify Nuvoton M23/M23_NS support as blocked on `numicro.c`
  flash-region review.
- [x] Classify Zephyr SDK `rv32m1` and `nds32` as target-backend decisions.
- [x] Classify RISC-V collaboration changes as core backend work requiring
  broad regression coverage.
- [x] Classify Arduino OpenOCD deltas as deferred unless NDS32 is restored.
- [x] Record ecosystems already covered locally and leave them unchanged.
- [x] Add `support/modules/*` metadata entries for deferred or blocked backend
  queues.
- [x] Record exact acceptance gates for each future backend/hardware batch.
- [x] Validate that no broken Tcl-only imports were added.

Phase 10 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase10-backend-hardware-queue.md` |
| Runtime imports | None. Remaining candidates require paired C backend or real hardware validation. |
| Metadata added | TI hardware validation, Espressif, WCH, Nuvoton, Zephyr SDK targets, RISC-V collaboration, and Arduino OpenOCD module records. |
| TI hardware status | Blocked on real XDS100/XDS110 plus recoverable C2000 hardware. |
| Backend status | Deferred to focused Phase 11 batches. |
| Covered ecosystems | Microchip, ST, Nordic, NXP, Silicon Labs, GigaDevice, Raspberry Pi, and TI native SWD remain covered locally. |

## Phase 11: Support Validation Tooling

- [x] Pick a local implementation batch that does not require unsafe hardware
  or unvalidated backend imports.
- [x] Add a dependency-free PowerShell validator for the Zephyr-style
  `support/` metadata tree.
- [x] Validate support metadata status values against the repository support
  vocabulary.
- [x] Validate support metadata references to `tcl/`, `docs/`, `examples/`,
  `tools/`, and `support/` paths.
- [x] Record the implementation decision and validation command.
- [x] Move real hardware and native backend implementation work into Phase 12.

Phase 11 result:

| Field | Decision |
| --- | --- |
| Result note | `docs/development/vendor-audit-phase11-support-validation-tooling.md` |
| Implementation | `tools/support/validate-support-metadata.ps1` |
| Hardware/backend imports | None; no matching hardware or simulator validation is available in this workspace. |
| Validation | Support metadata path and status validation passed with `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\support\validate-support-metadata.ps1`. |

## Phase 12: Hardware And Native Backend Implementation Queue

- [ ] Run TI hardware attach and C28x operation tests when real hardware is
  available.
- [ ] Pick one deferred backend family and import it as a complete C/Tcl/test
  batch.
- [ ] Start with Espressif, WCH, Nuvoton, RISC-V, Arduino/NDS32, or native
  AVRDUDE protocol ports only when matching validation hardware or simulator
  coverage is available.
