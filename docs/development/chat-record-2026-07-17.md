# OpenOCD integration chat record - 2026-07-17

This document records the development requests, decisions, implementation work,
and verification discussed during the OpenOCD integration session. It is an
engineering summary of the chat rather than a verbatim transcript.

## Initial merge requests

The work began with requests to merge changes into this OpenOCD tree from these
local sources:

- `C:\Users\livanyi\Downloads\openocd-unified-2026.07.17-source\openocd-unified-2026.07.17`
- `C:\Users\livanyi\Desktop\WORK\GIT\openocd\gens`
- `E:\GIT\open_microchip_tools`

The resulting tree incorporated TI XDS100 and Microchip programmer work,
including target, flash, interface, programmer, documentation, test, and example
files. Generated source archives under `gens/` were retained as project inputs.

## Microchip support objective

The requested Microchip scope covered PICkit 2, PICkit 3, PICkit 4, and ICD 4,
plus local SVD files under:

```text
C:\Users\livanyi\Desktop\WORK\GIT\openocd\svd
```

The implementation distinguishes the programmer generations because they do
not share one USB protocol:

| Tool | Supported path in this tree |
|---|---|
| PICkit 2 | `pk2cmd` command integration |
| PICkit 3 | MPLAB IPECMD or compatible legacy `pk2cmd` firmware |
| PICkit 4 | MPLAB IPECMD, CMSIS-DAP where applicable, and native RI4 USB |
| ICD 4 | MPLAB IPECMD, CMSIS-DAP where applicable, and native RI4 USB |

PICkit 2 and PICkit 3 are not RI4 probes. The clean-room reference project did
not provide native implementations of their older protocols, so the native RI4
driver applies only to PICkit 4 and ICD 4.

## SVD output

The following generated SVD files were placed under `svd/` and validated as
XML/SVD data:

- `dspic30f5011.svd`
- `dspic33fj128mc802.svd`
- `dspic33fj128mc804.svd`
- `dspic33ep128gm604.svd`

The directory also contains a README describing their provenance and scope.

## Rejected bridge design

An early RI4 integration used an external Python process started by PowerShell
or POSIX shell. OpenOCD connected to it through newline-delimited JSON over TCP
at `127.0.0.1:9123`.

The user explicitly rejected this architecture because it required environment
variables, a launcher script, Python dependencies, a second process, and a
local TCP protocol for operations that should occur inside OpenOCD.

The rejected launcher performed the equivalent of:

```powershell
python -m mchp_openocd.bridge_server --host 127.0.0.1 --port 9123
```

The PowerShell and shell launchers were removed. RI4 configuration no longer
accepts host or port settings, and the native target does not include socket,
JSON, or bridge-server code.

## Native C architecture

The replacement is an in-process C implementation split into two layers:

- `src/target/mchp_ri4_bridge.c` implements OpenOCD target callbacks, register
  access, memory operations, breakpoints, watchpoints, image programming,
  verification, reset handling, and Tcl commands.
- `src/target/mchp_ri4_native.c` implements script-catalog loading, direct
  libusb access, RI4 framing, transfer recovery, and named script execution.

The historical target type name `mchp_ri4_bridge` remains as a compatibility
alias for existing Tcl configuration. It no longer indicates a network bridge.

### USB transport

The native driver opens a probe by VID, PID, and optional serial number, claims
USB interface 0, and uses the RI4 endpoints directly:

| Channel | Direction | Endpoint |
|---|---|---:|
| Side channel | OUT | `0x02` |
| Side channel | IN | `0x81` |
| Data channel | OUT | `0x04` |
| Data channel | IN | `0x83` |

The implementation supports RI4 no-data, upload, and download script jobs,
result/acknowledgement validation, script-done messages, scripting-engine abort,
data-channel flush, and nuclear-reset recovery.

### Script catalogs

The native loader accepts:

- `scripts.xml`
- `scripts.yaml`
- `scripts.yaml.gz` when OpenOCD is built with zlib

Catalog loading is bounded to prevent uncontrolled memory use. Only matching
processor script names and byte arrays are retained.

An important correction made during the chat was that an EDC device YAML file
is not an RI4 script catalog. The correct input is the probe firmware catalog,
for example:

```text
E:/GIT/open_microchip_tools/vendor/mplabx_yaml_gz/packs/Microchip/PICkit4_TP/2.12.2541/firmware/scripts.yaml.gz
```

### Target operations

Native script dispatch covers:

- enter debug mode, halt, run, single-step, reset, and target status;
- get and set program counter where the selected family provides scripts;
- program-memory reads and writes;
- hardware breakpoints and data watchpoints;
- chip erase, image programming, and read-back verification;
- programming-mode entry and exit, including optional device-speed setup.

Capabilities are derived from scripts actually present for the selected
processor. Missing operations return an OpenOCD resource-not-available error
instead of pretending that the operation succeeded.

## Configuration

The native PICkit 4 flow is configured with the processor, family, script
catalog, and flash geometry:

```powershell
openocd `
  -c "set MCHP_RI4_PROCESSOR DSPIC30F5011" `
  -c "set MCHP_RI4_FAMILY DSPIC30F" `
  -c "set MCHP_RI4_SCRIPTS E:/GIT/open_microchip_tools/vendor/mplabx_yaml_gz/packs/Microchip/PICkit4_TP/2.12.2541/firmware/scripts.yaml.gz" `
  -c "set MCHP_RI4_FLASH_SIZE 0x12000" `
  -f programmer/microchip/pickit4-ri4.cfg `
  -c "program firmware.hex verify reset exit"
```

Use `programmer/microchip/icd4-ri4.cfg` for ICD 4 and select the matching ICD 4
firmware script catalog. MPLAB X/IPE must not claim the probe while OpenOCD owns
its USB interface.

## Build integration

The build system was updated to:

- compile `mchp_ri4_native.c` as part of `libtarget`;
- use the existing libusb-1.0 detection and flags;
- detect zlib for compressed catalogs;
- build without zlib while clearly rejecting `.gz` catalogs at runtime.

## Verification performed

The following checks were completed during the session:

- Both native RI4 C translation units passed MinGW GCC syntax checks with
  `-Wall -Wextra`, libusb, zlib, and the relevant OpenOCD feature definitions.
- The Microchip Python integration suite discovered 13 tests: 3 host-static
  tests passed and 10 Tcl tests were skipped because `tclsh` was not available
  on the default Windows PATH.
- `git diff --check` passed.
- Static checks confirmed removal of RI4 host, port, socket, Python launcher,
  and bridge-server references.
- Temporary build directories and compiler-check files were removed.

A complete linked OpenOCD build was not achieved in the session because the
bundled Jim Tcl make rules expected an in-tree Jim build while the verification
used an out-of-tree Windows build directory. This failure occurred before
linking the RI4 code and was separate from the C syntax checks.

## Remaining validation

Hardware testing is still required with physical PICkit 4 and ICD 4 probes and
representative devices from each intended family. That testing should cover:

1. USB enumeration and serial selection.
2. Script-catalog matching for the exact processor.
3. Debug entry, halt, run, step, reset, and polling.
4. Program-counter and memory operations.
5. Hardware breakpoint and watchpoint allocation.
6. Erase, program, verify, and recovery after an interrupted transfer.
7. Family-specific program-memory address and width behavior.

The primary end-user documentation remains in
`docs/programmers/microchip-pickit-icd.md`.
