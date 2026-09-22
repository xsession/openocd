# F28M35x VS Code Dual-Core Debug Example

This example shows the intended VS Code shape for a TI F28M35x Concerto board
using one XDS100v3 probe and one OpenOCD process.

Current hardware validation in this repository confirms the safe dual-core
OpenOCD server starts with two GDB ports:

```text
tms320f28m35x.m3    localhost:3333, target present but TAP disabled
tms320f28m35x.c28x  localhost:3334, examined and monitorable
```

Full simultaneous source debugging of both cores still needs two missing pieces:

- The Cortex-M3 TAP route must return a valid ARM DAP response. The current
  auto-enable test reaches the M3 TAP slot but gets `Invalid ACK (0)`.
- The C28x session needs a GDB executable that understands the `c28x`
  architecture. `arm-none-eabi-gdb` does not.

## Files

| File | Purpose |
| --- | --- |
| `tasks.json` | Starts OpenOCD, runs discovery, and sends monitor commands. |
| `launch.json` | Cortex-Debug external-server templates for the M3 and C28x sessions. |

Copy these files into your firmware workspace's `.vscode` folder, then adjust
the firmware paths and GDB paths.

## Working C28x Monitor Flow

From the OpenOCD repository root:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py preflight --preset f28m35x-dual-xds100v3
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py discover --preset f28m35x-dual-xds100v3 --elevate
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py server --preset f28m35x-dual-xds100v3 --elevate
```

Then run the VS Code task:

```text
F28M35x: monitor C28x snapshot
```

The monitor task uses OpenOCD's TCL port and prints:

```text
targets
poll
reg
```

## Monitor Both Cores From Cortex-Debug

The monitor-only path is the current VS Code workflow that does not program,
reset, halt, or source-step either core. It starts a tiny local GDB/RSP proxy on
two extra ports:

```text
M3 monitor proxy    localhost:3335
C28x monitor proxy  localhost:3336
OpenOCD TCL monitor localhost:6666
```

Use this sequence:

1. Run `F28M35x: preflight OpenOCD/XDS100v3`.
2. Run `F28M35x: start OpenOCD server`.
3. Run `F28M35x: start monitor-only GDB proxy`.
4. Launch `F28M35x: monitor both cores, no programming`.

The proxy gives Cortex-Debug and ordinary GDB a safe attach target, then
forwards `monitor ...` commands to OpenOCD's TCL monitor. It is intentionally
not a CPU-debug engine: register reads are placeholders, memory/control packets
fail closed, and source stepping stays disabled until the real M3 DAP route and
C28x GDB support are available.

Run this task only when you are actively investigating the M3 route:

```text
F28M35x: test M3 TAP route
```

It sets `F28M35X_M3_AUTO_ENABLE=1` before loading the OpenOCD config. On the
tested board, that enabled `tms320f28m35x.m3tap` but the Cortex-M DAP examine
failed with `Invalid ACK (0)`.

## Intended Simultaneous Debug Shape

```text
VS Code compound launch
  F28M35x Cortex-M3 via Cortex-Debug -> arm-none-eabi-gdb -> localhost:3333
  F28M35x C28x via Cortex-Debug      -> c28x-capable-gdb -> localhost:3334

single OpenOCD process
  tms320f28m35x.m3   cortex_m target
  tms320f28m35x.c28x c28x target

single XDS100v3 probe
  F28M35x ICEPick-C router
```

Do not start two OpenOCD processes for one XDS100v3 probe.

## Cortex-Debug Patch

The bundled Cortex-Debug patch is documented here:

```text
docs/openocd-course/external-patches/cortex-debug/0001-add-non-cortex-target-core-support.diff
```

It adds a `targetCore` option for non-Cortex targets such as `c2000`. That patch
does not make ARM GDB understand C28x; it only stops Cortex-Debug from assuming
every external OpenOCD target is an ARM Cortex target.

## Status

Use `F28M35x: monitor C28x snapshot` for direct OpenOCD TCL monitoring, or use
`F28M35x: monitor both cores, no programming` for the Cortex-Debug monitor-only
proxy path. Use the source-debug compound launch only after OpenOCD lists both
`tms320f28m35x.m3` and `tms320f28m35x.c28x` with M3 examined, and after a
C28x-capable GDB path is available.

A freshly built local Cortex-Debug was tested against the live dual OpenOCD
server without programming. M3 GDB attach was refused because the M3 target is
still examine-deferred, and C28x GDB attach failed with the available ARM GDB
because it does not understand `c28x`. The OpenOCD TCL monitor task remains the
working non-programming monitor path.

If preflight reports a connected `VID_0403&PID_6014` Digilent device instead of
`VID_0403&PID_A6D1`, the XDS100v3 is not the probe currently visible to Windows.
Connect the XDS100v3 or use a board/interface configuration for the actual
adapter.

If you need to fall back to the C28x-only OpenOCD server, use preset
`f28m35x-xds100v3`; that path exposes C28x on `localhost:3333`. The dual-core
preset exposes M3 on `localhost:3333` and C28x on `localhost:3334`.
