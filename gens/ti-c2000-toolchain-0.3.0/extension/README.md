# TI C2000 Debug for VS Code

`c2000-debug` is a Debug Adapter Protocol implementation for TI C2000 targets. It
adds C28x-aware debugging without pretending that C28x is an Arm Cortex-M core.

## Implemented DAP operations

- launch and attach;
- one or multiple cores represented as VS Code threads;
- source and instruction breakpoints;
- continue, pause, step into, step over, step out, reset and restart;
- CPU register inspection and register writes;
- expression evaluation through CCS GEL expressions;
- byte-addressed memory reads and writes with C28x 16-bit word conversion;
- one-frame PC/symbol stack fallback;
- program loading and optional verification through CCS Scripting;
- mock backend for CI and an experimental OpenOCD telnet backend.

## Recommended backend

Use `backend: "ccs"`. The extension starts the bundled JSON-lines bridge under
`<ccsRoot>/ccs/scripting/run.bat` or `run.sh`. TI's local installation supplies
the debugger and XDS probe support; those proprietary components are not bundled.

```jsonc
{
  "name": "F28069: XDS110",
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
  "runToEntryPoint": "main"
}
```

Install `mcu-debug.peripheral-viewer` for the SVD tree. The adapter implements
DAP `readMemory` and `writeMemory`, and the repository's generated C28x SVDs are
byte-addressed specifically for this integration.

## F28M35x multicore

A single CCS launch can expose the C28x and Cortex-M3 sessions as separate DAP
threads. Each core can load its own executable:

```jsonc
{
  "name": "F28M35x: both cores",
  "type": "c2000-debug",
  "request": "launch",
  "backend": "ccs",
  "device": "tms320f28m35x",
  "ccsRoot": "C:/ti/ccs2040",
  "ccxml": "${workspaceFolder}/targetConfigs/F28M35x_XDS110.ccxml",
  "cores": [
    {
      "name": "C28x control subsystem",
      "pattern": "C28xx|C28x",
      "architecture": "c28x",
      "device": "tms320f28m35x_c28x",
      "addressScale": 2,
      "executable": "${workspaceFolder}/Debug/c28x.out"
    },
    {
      "name": "Cortex-M3 communication subsystem",
      "pattern": "Cortex_M3|CortexM3|M3",
      "architecture": "cortex-m3",
      "device": "tms320f28m35x_m3",
      "addressScale": 1,
      "executable": "${workspaceFolder}/Debug/m3.out"
    }
  ]
}
```

## Build and test

```sh
npm run build
npm test
npm run package
```

The hardware-independent suite tests DAP framing and behavior, C28x address
translation, and the CCS bridge against a fake CCS Scripting module. Real XDS
probe and flash verification must be run on the intended board and `.ccxml`.
## OpenOCD/XDS100 integration

Release 0.3.0 includes the OpenOCD XDS100v2/v3 overlay under `../openocd`.
Apply it to the `xsession/openocd` checkout, start OpenOCD with the appropriate
`interface/ftdi/xds100v2.cfg` or `xds100v3.cfg`, then select the `openocd`
backend in this extension. Ready-made launch and task files are under
`../examples/vscode`.

