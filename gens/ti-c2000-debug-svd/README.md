# TI C2000 + MSPM0 SVD and VS Code debug stack

This repository provides two related deliverables:

1. reproducible CMSIS-SVD generation for selected TI devices;
2. an installable VS Code Debug Adapter for C2000 C28x targets.

Supported device profiles:

- MSPM0C1103;
- TMS320F28069;
- TMS320F280049;
- TMS320F28M35x Concerto C28x subsystem;
- TMS320F28M35x Concerto Cortex-M3 subsystem.

## What is implemented

### SVD generator

- MSPM0C1103 extraction from TI's CMSIS device pack;
- C2000 conversion from the installed CCS target database;
- C28x 16-bit word-address to byte-address normalization;
- deterministic patch files;
- XML, register, field and debugger-profile validation;
- VS Code launch configuration generation.

### `c2000-debug` VS Code extension

- Debug Adapter Protocol implementation;
- production CCS Scripting backend using local TI debugger/XDS support;
- C28x-aware byte/word memory conversion;
- source and instruction breakpoints;
- continue, pause, reset, restart and stepping;
- CPU register view and register writes;
- GEL expression evaluation;
- program load and optional verification;
- one or multiple CCS cores represented as VS Code threads;
- F28M35x dual-core launch definition;
- standalone SVD viewer compatibility through `svdPath` and DAP memory requests;
- deterministic mock backend and automated integration tests;
- experimental OpenOCD telnet backend.

The extension does not redistribute TI proprietary debugger components. It uses the
user's installed Code Composer Studio scripting environment.

## Compatibility matrix

| Device | Debug adapter | SVD viewer | Notes |
|---|---|---|---|
| MSPM0C1103 | Cortex-Debug | Yes | Native Cortex-M0+ target |
| F28M35x M3 | Cortex-Debug or `c2000-debug` | Yes | Cortex-M3 communication subsystem |
| F28M35x C28x | `c2000-debug` | Yes | C28x control subsystem |
| F28069 | `c2000-debug` | Yes | C28x + FPU/VCU profile |
| F280049 | `c2000-debug` | Yes | C28x + FPU/TMU/VCU profile |

Cortex-Debug remains the recommended adapter for Arm Cortex-M targets. C28x is
handled by the included `c2000-debug` adapter rather than by falsely describing the
CPU as Cortex-M.

## Quick start

### 1. Install the extension

Build locally:

```sh
cd extension
npm test
npm run package
```

Install the resulting file:

```sh
code --install-extension extension/c2000-debug-0.1.0.vsix
```

Also install `mcu-debug.peripheral-viewer` for the SVD tree.

### 2. Generate SVD files

Windows:

```powershell
.\scripts\bootstrap.ps1
.\.venv\Scripts\ti-svd.exe discover --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate tms320f28069 --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate tms320f280049 --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate tms320f28m35x_c28x --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate tms320f28m35x_m3 --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate mspm0c1103
```

Linux:

```sh
./scripts/bootstrap.sh
ti-svd discover --ccs-root "$HOME/ti"
ti-svd generate-all --ccs-root "$HOME/ti"
```

A typical target database is under:

```text
C:\ti\ccsXXXX\ccs\ccs_base\common\targetdb
```

Pass it explicitly with `--targetdb` when several CCS versions are installed.

### 3. Generate a C2000 launch configuration

```powershell
.\.venv\Scripts\ti-svd.exe vscode-config tms320f28069 `
  --backend ccs `
  --ccs-root C:/ti/ccs2040 `
  --ccxml '${workspaceFolder}/targetConfigs/F28069_XDS110.ccxml' `
  --executable '${workspaceFolder}/Debug/app.out' `
  --output .vscode/f28069.json
```

Generated C28x configuration:

```jsonc
{
  "name": "TMS320F28069 (ccs)",
  "type": "c2000-debug",
  "request": "launch",
  "backend": "ccs",
  "device": "tms320f28069",
  "ccsRoot": "C:/ti/ccs2040",
  "ccxml": "${workspaceFolder}/targetConfigs/F28069_XDS110.ccxml",
  "corePattern": "C28xx|C28x",
  "executable": "${workspaceFolder}/Debug/app.out",
  "svdPath": "${workspaceFolder}/svd/tms320f28069.svd",
  "addressScale": 2,
  "registerProfile": "auto",
  "runToEntryPoint": "main"
}
```

For MSPM0C1103 and the F28M35x M3 profile, `ti-svd vscode-config` continues to emit
normal Cortex-Debug configurations unless `--adapter c2000-debug` is selected.

## CCS bridge

`bridge/ccs-debug-bridge.js` runs through:

```text
<CCS root>/ccs/scripting/run.bat
<CCS root>/ccs/scripting/run.sh
```

It maps JSON-lines commands to CCS Scripting operations such as `configure`,
`openSession`, `target.connect`, `memory.loadProgram`, `breakpoints.add`,
`registers.read`, `expressions.evaluate`, `memory.read`, and target stepping.
Untagged CCS output is forwarded to the VS Code Debug Console.

## C28x address model

SVD and DAP addresses are bytes. C28x target addresses are normally 16-bit words.
The adapter and bridge use `addressScale: 2`:

```text
byte address = target word address * 2
```

Unaligned byte reads and writes use covering 16-bit reads and read-modify-write.
This allows generic VS Code memory and peripheral viewers to access C28x registers
without embedding C28x-specific logic.

## F28M35x multicore

The CCS backend can open several sessions from one `.ccxml`; each appears as a DAP
thread. See:

```text
examples/vscode/c2000-f28m35x-multicore.launch.jsonc
```

The C28x and M3 sides keep separate executables, architecture profiles, address
scales and SVD files. A launch has one primary `svdPath`; switch it to the SVD for
the core whose peripherals you are inspecting.

## Validation and tests

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
cd extension
npm test
npm run package
```

The test suite covers:

- TI target XML conversion and C28x address scaling;
- Cortex-M and C28x SVD validation profiles;
- launch configuration generation;
- DAP framing and a representative debug session;
- memory/register/breakpoint operations;
- CCS bridge behavior against a fake scripting installation;
- VSIX construction.

Hardware validation is still required for each `.ccxml`, XDS probe, board reset
sequence and flash algorithm. Follow [docs/hardware-validation.md](docs/hardware-validation.md).

## Repository map

```text
bridge/          CCS Scripting JSON bridge
extension/       installable c2000-debug VS Code extension
src/ti_svd/      SVD generator and launch-config CLI
devices/         device source and address metadata
patches/         deterministic SVD corrections
svd/             generated SVD outputs
examples/vscode/ launch configurations
tests/           Python generator tests
docs/            debugger, addressing and validation documentation
```
