# Phase 1 TI Vendor Audit Triage

This records Phase 1 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Source Pin

| Field | Value |
| --- | --- |
| Ecosystem | Texas Instruments |
| Repository | `https://github.com/TexasInstruments/ti-openocd.git` |
| Branch | `ti-release` |
| Pinned commit | `cb22a31e503b39820f0c758531cb9949300d014c` |
| Tag | `ti-v1.5.0.75` |
| Commit subject | `Pull request #37: Reset problem fix for MSPM33` |
| Commit date | `2026-07-02 14:02:10 -0500` |
| Local checkout | `artifacts/vendor-audit/checkouts/texas-instruments` |
| Delta CSV | `artifacts/vendor-audit/openocd-vendor-file-delta.csv` |

Audit command:

```powershell
.\tools\vendor\openocd-vendor-audit.ps1 -Fetch
```

Result:

```text
Wrote 6758 file delta rows to artifacts/vendor-audit/openocd-vendor-file-delta.csv
```

Texas Instruments rows:

| Status | Count |
| --- | ---: |
| `changed` | 551 |
| `new-upstream` | 143 |

Top-level TI row groups:

| Group | Count |
| --- | ---: |
| `tcl/board` | 168 |
| `src/target` | 163 |
| `tcl/interface` | 103 |
| `tcl/target` | 99 |
| `src/flash` | 87 |
| `src/jtag` | 59 |

## New Tcl Triage

The TI fork stores many files as flat names such as `ti_mspm33.cfg`. This
repository normalizes TI files into directories such as `tcl/target/ti/mspm33.cfg`.
That means many audit rows look like `new-upstream` even though the support is
already present locally.

### Interface Files

| Upstream file | Decision |
| --- | --- |
| `tcl/interface/chameleon.cfg` | Deferred. Not part of the TI C2000/XDS lane. |
| `tcl/interface/flashlink.cfg` | Deferred. Not part of the TI C2000/XDS lane. |

### Board Files

After normalizing `ti_*.cfg` names into `tcl/board/ti/*.cfg`, nearly all TI
board rows already exist locally.

| Upstream file | Normalized/local decision |
| --- | --- |
| `tcl/board/ti_am13e230x_launchpad.cfg` | Duplicate of local `tcl/board/ti/am13e230x-launchpad.cfg`. |
| `tcl/board/ti_cc35x1e_launchpad.cfg` | Duplicate of local `tcl/board/ti/cc35x1e-launchpad.cfg`. |
| `tcl/board/ti_lp_em_cc*.cfg` | Duplicate of local `tcl/board/ti/lp-em-cc*.cfg` files. |
| `tcl/board/ti_mspm33_launchpad.cfg` | Duplicate of local `tcl/board/ti/mspm33-launchpad.cfg`. |
| `tcl/board/ti_am625_swd_native.cfg` | Covered by local `tcl/board/ti/am625-self-hosted.cfg`; no direct import. |
| `tcl/board/ti_j721e_swd_native.cfg` | Covered by local `tcl/board/ti/j721e-self-hosted.cfg`; no direct import. |
| `tcl/board/ti_beagleboard*.cfg`, `ti_beaglebone*.cfg` | Covered by local `tcl/board/beagle/*.cfg`; no direct TI-path import. |

### Target Files

After normalizing `ti_*.cfg` names into `tcl/target/ti/*.cfg`, all high-value
TI target rows checked in this lane already exist locally.

| Upstream file | Normalized/local decision |
| --- | --- |
| `tcl/target/icepick.cfg` | Local equivalent exists as `tcl/target/ti/icepick.cfg`; compare only if ICEPick routing bugs appear. |
| `tcl/target/ti_am13e230x.cfg` | Duplicate of local `tcl/target/ti/am13e230x.cfg`. |
| `tcl/target/ti_cc23xx.cfg`, `ti_cc27xx.cfg`, `ti_lpf3.cfg` | Duplicate of local LPF3 target batch. |
| `tcl/target/ti_mspm0.cfg`, `ti_mspm33.cfg` | Duplicate of local TI MSP target files. |
| `tcl/target/ti_k3.cfg` and AM/Davinci/TMS570 files | Duplicate or already covered locally; outside the immediate C2000/XDS lane. |

Phase 1 config conclusion: there is no obvious standalone TI Tcl import for
Phase 2. The next work should compare selected existing local files against the
pinned TI fork only where the C2000/XDS hardware path needs it.

## Modified C Backend Triage

The full TI audit includes many changed C files because this repository and the
TI fork have different baselines. For the chosen lane, the relevant changed C
files are:

| File | Category | Decision |
| --- | --- | --- |
| `src/jtag/drivers/xds110.c` | Backend batch | Compare for XDS110 fixes after XDS100v3 detection path is stable. |
| `src/jtag/drivers/ftdi.c` | Backend batch | Review only if XDS100v2/v3 FTDI behavior differs on hardware. High regression risk. |
| `src/jtag/drivers/ti_icdi_usb.c` | Backend batch | Defer. Related to TI ICDI, not C2000/XDS100. |
| `src/flash/nor/mspm0.c` | Backend batch | Defer for MSPM0 lane. Not C2000/XDS100. |
| `src/flash/nor/cc26xx.c` | Backend batch | Defer for SimpleLink lane. Not C2000/XDS100. |
| `src/flash/nor/cc3220sf.c` | Backend batch | Defer for SimpleLink lane. Not C2000/XDS100. |
| `configure.ac`, `Makefile.am` | Build glue | Review only with a concrete backend import. |

The audit also reports broad changes under `src/target` and `src/flash/nor`.
Those are not safe to import as a block.

## File Categories

| Category | Files |
| --- | --- |
| Importable config | None selected in Phase 1. Most relevant TI Tcl files are already present after local path normalization. |
| Backend batch | `src/jtag/drivers/xds110.c`, possibly `src/jtag/drivers/ftdi.c` if XDS100 hardware testing shows a transport issue. |
| Duplicate | Normalized TI board and target files already present under `tcl/board/ti/` and `tcl/target/ti/`. |
| Obsolete or outside lane | Beagle flat TI board aliases, old board naming, non-C2000 AM/K3/Davinci/TMS570 work. |
| Unsupported closed protocol | No new closed-protocol import selected for this phase. Existing TI unsupported configs remain explicit fail-closed placeholders. |

## License/SPDX Check

Sampled files planned or considered for later comparison all have
OpenOCD-compatible SPDX headers:

| File | Header result |
| --- | --- |
| `tcl/interface/ftdi/xds100v2.cfg` | `# SPDX-License-Identifier: GPL-2.0-or-later` |
| `tcl/interface/ftdi/xds100v3.cfg` | `# SPDX-License-Identifier: GPL-2.0-or-later` |
| `src/jtag/drivers/xds110.c` | `// SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |
| `src/flash/nor/mspm0.c` | `// SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |
| `src/flash/nor/cc26xx.c` | `// SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |
| `src/flash/nor/cc3220sf.c` | `// SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |
| `tcl/target/icepick.cfg` | `# SPDX-License-Identifier: GPL-2.0-or-later` |
| `tcl/target/ti_mspm33.cfg` | `# SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |
| `tcl/target/ti_am13e230x.cfg` | `# SPDX-License-Identifier: GPL-2.0-or-later` plus TI copyright. |

Every file imported in a later phase still needs its own header check at import
time.

## Why This Batch Is Useful

The TI lane is the best next batch because it matches the active hardware goal:
detecting and validating TI C2000 devices, especially F28M35x dual-core devices,
through XDS100-family probes. The audit shows the local tree already contains
most TI Tcl coverage, so the next useful work is not more file copying. It is a
focused hardware/backend pass: XDS100v3 discovery, XDS110 comparison only where
needed, ICEPick secondary-TAP discovery, and C28x target creation validation.
