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

- [ ] Identify the CPU architecture and confirm OpenOCD has a target backend
  for it.
- [ ] Add the target Tcl file with real TAP, DAP, or debug-module IDs.
- [ ] Define work-area RAM only after checking the memory map.
- [ ] Prove `scan_chain`, `dap info`, or the target equivalent returns the
  expected ID.
- [ ] Prove `targets` lists the expected target.
- [ ] Prove halt, resume, step, register read, and memory read.
- [ ] Document reset quirks, boot-mode requirements, and debug lock behavior.

## Phase 5: Flash Support

- [ ] Decide whether an existing flash driver can be reused.
- [ ] If new, add the flash driver under `src/flash/nor/`.
- [ ] Register the flash driver in `Makefile.am`, `driver.h`, and `drivers.c`.
- [ ] Add any required RAM loader under `contrib/loaders/flash/`.
- [ ] Prove flash probe reports the expected device or MCU variant.
- [ ] Prove erase, write, verify, protect, and unlock behavior.
- [ ] Test failure cases such as protected sectors and wrong alignment.
- [ ] Add flash examples only after real hardware verification.

## Phase 6: Board Files And Examples

- [ ] Add board files that combine the real programmer and target.
- [ ] Keep board files non-destructive by default.
- [ ] Add examples under `examples/<vendor_or_family>/` when they help users.
- [ ] Include low-speed first-attach commands for unstable or new hardware.
- [ ] Include a GDB or telnet workflow when debug support is ready.
- [ ] Include flash commands only when flash support is verified.

## Phase 7: Build And Regression Validation

- [ ] Run a native build with the required configure flags.
- [ ] Run the Windows package build if the feature affects Windows users.
- [ ] Run config-load checks for all new scripts.
- [ ] Run hardware attach checks on the real board and programmer.
- [ ] Run flash checks on sacrificial or recoverable hardware.
- [ ] Check that unrelated existing board configs still load.
- [ ] Save exact commands and results in documentation.

## Phase 8: Documentation And Support Status

- [ ] Add or update target docs under `docs/targets/`.
- [ ] Add or update programmer docs under `docs/programmers/`.
- [ ] Add development notes when the support is partial or experimental.
- [ ] State exact tested hardware, OS, probe firmware, and OpenOCD command.
- [ ] State known limits clearly, especially closed protocols and unverified
  flash operations.
- [ ] Update `docs/index.md` if the page is user-facing.
- [ ] Update the vendor audit page with the integration decision.

## Phase 9: Current Audit Queue

- [ ] TI hardware path: finish XDS100v2/XDS100v3/XDS110 packaging, attach flow,
  and C28x target creation tests.
- [ ] Espressif backend batch: import ESP32-C5, ESP32-C61, ESP32-P4, H21, H4,
  or S31 only with their required C target and flash backend changes.
- [ ] WCH backend batch: import CH32 support only with WCH adapter, transport,
  target, and flash code together.
- [ ] Nuvoton backend batch: update `numicro.c` flash-region handling before
  adding M23 and M23_NS target aliases.
- [ ] Zephyr SDK deferred targets: handle `rv32m1` or `nds32` only after
  deciding whether their target backends belong in this fork.
- [ ] RISC-V collaboration: review core RISC-V behavior after MCU-specific
  imports, because regressions affect many targets.
- [ ] Arduino OpenOCD: import only after deciding whether old NDS32/package flow
  files are still useful.
- [ ] Microchip, ST, Nordic, NXP, Silicon Labs, GigaDevice, and Raspberry Pi:
  leave as covered unless a newer source adds a self-contained, tested file.
