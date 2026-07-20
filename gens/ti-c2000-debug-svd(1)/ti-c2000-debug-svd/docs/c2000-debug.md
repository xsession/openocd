# C2000 debug adapter

The repository now contains an installable VS Code extension under `extension/`.
It uses the Debug Adapter Protocol directly and therefore does not require C28x to
look like an Arm Cortex-M target.

## Production path: CCS Scripting

The `ccs` backend starts `bridge/ccs-debug-bridge.js` with the scripting runner
from the user's CCS installation. The bridge configures the supplied `.ccxml`,
opens one or more core sessions, connects through the selected XDS probe, and
maps JSON requests to TI debugger operations.

Implemented bridge operations:

- configure and list cores;
- connect and disconnect;
- load and optionally verify a program;
- run, halt, reset, source-step and assembly-step;
- source, symbolic and address breakpoints;
- CPU register reads and writes;
- GEL expression evaluation;
- memory reads and writes;
- PC and nearest-symbol stack fallback;
- asynchronous halt detection after continue.

No TI binaries are redistributed. The bridge imports the local CCS scripting
module or is run by CCS's `run.bat`/`run.sh`.

## C28x addressing boundary

DAP and SVD viewers use byte addresses. C28x debug APIs use target address units
that are normally 16-bit words. `addressScale: 2` establishes the boundary:

```text
DAP/SVD byte address 0x00002000 -> C28x target address 0x00001000
```

Unaligned byte reads and writes are supported. The bridge reads every covering
16-bit word and performs a read-modify-write when only one byte of a word changes.
Instruction breakpoint addresses must be word aligned.

## Register profiles

- `c28x`: base CPU registers;
- `c28x-fpu-vcu`: F28069-oriented profile;
- `c28x-fpu-tmu-vcu`: F280049-oriented profile;
- `cortex-m3`: F28M35x communication subsystem;
- `auto`: selects a profile from the device name.

Unsupported register names are omitted at runtime because availability can differ
between device revisions and CCS target descriptions.

## Current stack limitation

The current public CCS Scripting object model exposes target control, registers,
memory, expressions, symbols and breakpoints, but not a complete call-stack/local
variable enumeration API. The adapter therefore returns a reliable one-frame PC
plus nearest-symbol fallback. Expressions and register inspection remain fully
available. A future backend can use a TI-specific stack API when one is available
in the installed CCS release.

## Experimental OpenOCD backend

The OpenOCD backend connects to the telnet port of an already-running server. It
implements halt, resume, reset, instruction step, registers, memory and address
breakpoints. Source-level symbols, flash loading and automatic stop notifications
remain CCS-backend features until the custom C28x OpenOCD server exposes a complete
remote-debug interface.
