# Renode `custom-cores` integration

This repository supports the C2000 implementation in:

```text
https://github.com/xsession/renode/tree/custom-cores
```

The integration deliberately uses Renode's Monitor protocol instead of assuming
that a standard C28x GDB client is available. The branch identifies the CPU's GDB
architecture as `c2000`, but its C2000 class currently returns an empty GDB feature
description. The Monitor still exposes registers, system-bus access, stepping,
execution control and CPU hooks.

## Supported branch platforms

| Device | Renode platform file | Adapter status |
|---|---|---|
| TMS320F28069 | `platforms/cpus/ti/tms320f28069.repl` | Integrated |
| TMS320F280049 | `platforms/cpus/ti/tms320f280049c.repl` | Integrated |
| TMS320F28M35x | none in the inspected branch | Not yet emulatable |

The `c` suffix in the F280049 platform filename belongs to the Renode branch; the
VS Code device identifier remains `tms320f280049`.

## Launch Renode from VS Code

```jsonc
{
  "name": "TMS320F28069 in Renode custom-cores",
  "type": "c2000-debug",
  "request": "launch",
  "backend": "renode",
  "device": "tms320f28069",
  "renodePath": "C:/tools/renode/renode.exe",
  "renodeScript": "${workspaceFolder}/examples/renode/f28069.resc",
  "renodeMonitorPort": 1234,
  "renodeCpu": "cpu",
  "renodeSysbus": "sysbus",
  "executable": "${workspaceFolder}/build/application.out",
  "svdPath": "${workspaceFolder}/svd/tms320f28069.svd",
  "addressScale": 2
}
```

The adapter starts Renode in headless telnet-monitor mode, includes the `.resc`,
loads an ELF/TI EABI `.out`, pauses the machine, and opens one DAP thread.
Use `renodeLaunch: false` with `request: "attach"` to connect to a monitor that is
already running.

## Implemented operations

- register reads and writes for the exact 32-register mapping exposed by the branch;
- C28x byte-to-word memory translation, including unaligned read-modify-write;
- continue, pause, reset and instruction stepping;
- instruction-address breakpoints implemented with Renode CPU hooks;
- program loading through `sysbus LoadELF` or `sysbus LoadBinary`;
- optional symbol name lookup for the current PC;
- automatic Renode process launch and monitor connection retry;
- SVD access through standard DAP `readMemory` and `writeMemory` requests.

## Current branch limitations

These are limitations of the inspected emulator branch, not hidden by the adapter:

1. Its committed C2000 smoke log reaches the completion marker and then reports a
   process core dump during shutdown.
2. The minimal C2000 smoke platform states that memory-store instructions are not
   implemented yet.
3. The C2000 GDB feature list is empty, so a conventional GDB register-description
   handshake is incomplete.
4. No F28M35x platform description was found.
5. Source-line breakpoints require a later symbol/line mapper; the Monitor backend
   currently accepts instruction-address breakpoints.

The adapter terminates a Renode process with `SIGTERM` instead of sending `quit`,
which avoids depending on the branch's currently failing shutdown path.

## Verify another checkout

```sh
python scripts/check_renode_custom_cores.py \
  --renode-root /path/to/renode \
  --infrastructure-root /path/to/renode-infrastructure
```

The command verifies the CPU class, exact register mapping, supported platform
files and the status of the branch's own smoke-test log. A snapshot of the result
used for this release is stored in:

```text
reports/renode-custom-cores-compatibility.json
```

## Branch fixes required for production firmware

A complete production-grade Renode backend still requires work in the emulator:

- finish C28x load/store and remaining instruction coverage;
- expose a proper GDB target description or retain Monitor as the primary debugger;
- fix the shutdown core dump;
- add F28M35x C28x and Cortex-M3 platform integration;
- validate peripheral interrupt, flash, CLA, FPU, VCU and TMU behavior against TI
  reference tests.
