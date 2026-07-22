# VS Code Dual-Core Debug For TI F28M35x

F28M35x Concerto devices contain a Cortex-M3 subsystem and a C28x/C2000
subsystem behind a TI ICEPick-C JTAG router. The correct parallel-debug shape
is:

```text
one XDS100v3 USB probe
one OpenOCD process
two OpenOCD targets
two GDB ports
two VS Code debug sessions
```

Do not start two OpenOCD processes for one XDS100v3. Only one process can own
the USB/JTAG probe.

## Current Repository Status

The conservative `target/ti/tms320f28m35x.cfg` creates the C28x target endpoint
and ICEPick discovery helpers.

The opt-in dual-core configuration is:

```text
target/ti/tms320f28m35x-dual-core.cfg
board/ti/tms320f28m35x-dual-core-xds100v3.cfg
board/ti/tms320f28m35x-dual-core-xds100v2.cfg
```

It enables the CCS-discovered ICEPick subpaths:

```text
M3   port 0x10, ARM CoreSight TAP ID 0x4ba00477, auto-enable off by default
C28x port 0x11, C28x ProcID 0x5000A3F8
```

The ready-to-copy VS Code example lives here:

```text
examples/vscode/f28m35x-cortex-debug/
```

Use this command first:

```powershell
python .\tools\support\c28x_openocd_wrapper.py discover --preset f28m35x-dual-xds100v3 --elevate
```

Record the SDTAP output. After that, start OpenOCD and monitor the C28x target:

```powershell
python .\tools\support\c28x_openocd_wrapper.py server --preset f28m35x-dual-xds100v3 --elevate
python .\tools\support\c28x_openocd_wrapper.py monitor targets poll reg
```

If dual-core init fails on the M3 TAP, fall back to the validated C28x-only
preset:

```powershell
python .\tools\support\c28x_openocd_wrapper.py server --preset f28m35x-xds100v3 --elevate
```

To intentionally reproduce the M3 route test:

```powershell
python .\tools\support\c28x_openocd_wrapper.py probe `
  --preset f28m35x-dual-xds100v3 `
  --set F28M35X_M3_AUTO_ENABLE=1 `
  --elevate
```

On the tested board, that enabled `tms320f28m35x.m3tap` but the M3 DAP examine
returned `Invalid ACK (0)`.

## Parallel Debug Model

```mermaid
flowchart LR
  VS1["VS Code Cortex-Debug\nM3 firmware"] --> GDB1["arm-none-eabi-gdb\nlocalhost:3333"]
  VS2["VS Code C28x debug session\nC28x firmware"] --> GDB2["C28x-capable GDB/debugger\nlocalhost:3334"]
  GDB1 --> OCD["single OpenOCD process"]
  GDB2 --> OCD
  OCD --> XDS["XDS100v3"]
  XDS --> ICE["F28M35x ICEPick-C"]
  ICE --> M3["Cortex-M3"]
  ICE --> C28["C28x"]
```

## VS Code Compound Shape

Use a compound launch only after OpenOCD exposes both targets.
For the shared PIC, AVR, C2000 and generic multi-core launch templates, see
`tools/vscode/cortex-debug/support/openocd-mcu-launch-examples.json` and
`docs/usage/vscode-cortex-debug-openocd-mcus.md`.

For a user workspace copy/paste example, use:

```text
examples/vscode/f28m35x-cortex-debug/launch.json
examples/vscode/f28m35x-cortex-debug/tasks.json
```

```json
{
  "version": "0.2.0",
  "compounds": [
    {
      "name": "F28M35x: M3 + C28x",
      "configurations": [
        "F28M35x Cortex-M3",
        "F28M35x C28x"
      ],
      "stopAll": true
    }
  ],
  "configurations": [
    {
      "name": "F28M35x Cortex-M3",
      "type": "cortex-debug",
      "request": "attach",
      "servertype": "external",
      "cwd": "${workspaceFolder}",
      "executable": "${workspaceFolder}/build/m3.elf",
      "gdbPath": "arm-none-eabi-gdb",
      "gdbTarget": "localhost:3333",
      "memoryAddressUnitBytes": 1,
      "runToEntryPoint": "main",
      "showDevDebugOutput": "raw"
    },
    {
      "name": "F28M35x C28x",
      "type": "cppdbg",
      "request": "launch",
      "cwd": "${workspaceFolder}",
      "program": "${workspaceFolder}/build/c28x.out",
      "MIMode": "gdb",
      "miDebuggerPath": "path/to/c28x-capable-gdb.exe",
      "miDebuggerServerAddress": "localhost:3334",
      "stopAtEntry": true
    }
  ]
}
```

Notes:

- Cortex-Debug is appropriate for the Cortex-M3 session.
- Cortex-Debug can monitor the C28x session through the monitor-only proxy
  documented in `examples/vscode/f28m35x-cortex-debug`.
- The C28x session requires a C28x-capable GDB/debug adapter frontend. If your
  TI toolchain does not provide GDB for C28x, use CCS or another TI-capable
  debug frontend for source stepping on that core.
- Both sessions must attach to the same OpenOCD process through different GDB
  ports.

With the patched Cortex-Debug submodule, the C28x template may use
`"targetCore": "c2000"` to avoid Cortex-specific defaults. That setting does
not replace the need for a C28x-capable GDB.

## OpenOCD Target Requirements

OpenOCD must create both targets before VS Code can attach:

```text
tms320f28m35x.m3    cortex_m    localhost:3333
tms320f28m35x.c28x  c28x        localhost:3334
```

The safe dual-core config now creates those two GDB services. Hardware
validation showed M3 on `3333` with its TAP disabled by default, and C28x on
`3334` examined and monitorable. The M3 route remains the next hardware
validation point before Cortex-Debug source stepping can work on that core.

For no-programming monitor-only work, start OpenOCD normally, then run:

```powershell
python .\tools\support\c28x_openocd_wrapper.py gdb-monitor-proxy
```

Attach Cortex-Debug to `localhost:3335` for the M3 monitor proxy and
`localhost:3336` for the C28x monitor proxy. These ports forward `monitor`
commands to OpenOCD's TCL monitor and do not provide source stepping.

## Bring-Up Order

1. Fix XDS100v3 WinUSB binding for `VID_0403&PID_A6D1&MI_00`.
2. Start one OpenOCD process.
3. Run ICEPick discovery.
4. Confirm which SDTAP is the Cortex-M3 and which is C28x.
5. Add or enable both target definitions in one OpenOCD config.
6. Confirm `targets` lists both cores.
7. Confirm OpenOCD opens two GDB ports.
8. Attach VS Code Cortex-Debug to the M3 port.
9. Attach the C28x debugger to the C28x port.

## First Evidence To Capture

```text
scan_chain
c2000_icepick_read_idcode
c2000_icepick_read_code
c2000_icepick_scan_sdtaps
c2000_icepick_scan_tsttaps
targets
```

Paste those results into the issue or support note before changing flash,
reset, or memory settings.
