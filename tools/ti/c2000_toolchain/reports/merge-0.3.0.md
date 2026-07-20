# Merge report: 0.3.0

## Merged inputs

- TI C2000/MSPM0 SVD generator and device manifests;
- `c2000-debug` VS Code extension;
- CCS Scripting bridge;
- Renode `custom-cores` monitor backend and compatibility report;
- OpenOCD XDS100v2/XDS100v3 FTDI support bundle.

## Consolidation changes

- one repository version: `0.3.0`;
- one installable extension: `c2000-debug-0.3.0.vsix`;
- OpenOCD patcher and overlay moved under `openocd/`;
- one root Makefile and CI workflow;
- unified architecture, migration, and XDS100 documentation;
- ready-made OpenOCD/XDS100 VS Code attach examples;
- stale 0.1.0 and 0.2.0 VSIX outputs removed;
- release archive validation added.

## Validation

- SVD/generator unit tests: 6 passed;
- VS Code extension/backend tests: 6 passed;
- OpenOCD patcher tests: 5 passed;
- OpenOCD Tcl configuration test: passed;
- OpenOCD static bundle validation: passed;
- patched FTDI fixture compilation: passed;
- VSIX construction: passed;
- unified ZIP integrity and required-member validation: passed.

## Hardware boundary

No physical XDS100 probe or C2000 board was connected during this merge. The
repository validates the transport patch, configuration, debugger protocol, and
packaging offline. Physical JTAG scan, halt, register access, reset, erase, and
programming remain board-level qualification steps.
