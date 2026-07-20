# Unified architecture

```text
VS Code
├── Cortex-Debug
│   ├── MSPM0C1103
│   └── F28M35x Cortex-M3
└── c2000-debug
    ├── CCS Scripting backend ── XDS100/XDS110/XDS200 ── physical C28x
    ├── OpenOCD telnet backend ── XDS100v2/v3 FTDI overlay ── physical C28x
    ├── Renode Monitor backend ── xsession/renode custom C2000 core
    └── mock backend ── deterministic CI

Peripheral viewer
└── byte-addressed CMSIS-SVD generated from TI metadata

Address boundary
└── C28x word address × 2 = DAP/SVD byte address
```

## Component ownership

- `src/ti_svd` owns source acquisition, conversion, patching, validation, and
  debugger configuration generation.
- `extension` owns DAP behavior and backend-independent C28x semantics.
- `bridge` owns TI CCS Scripting translation.
- `openocd` owns XDS100 FTDI transport initialization and installation into an
  OpenOCD source checkout.
- `examples/renode` and the Renode backend own emulator integration.

## Why C28x is not forced through Cortex-Debug

Cortex-Debug assumes an Arm Cortex-M execution model. C28x differs in CPU
registers, word addressing, instruction set, stack behavior, and debug
transport. The repository shares the SVD/peripheral-viewer workflow while using
a dedicated DAP adapter for C28x execution control.

## F28M35x

F28M35x is represented as two cores:

- C28x control subsystem using `c2000-debug`;
- Cortex-M3 communication subsystem using Cortex-Debug or a separate backend.

Each core keeps its own executable, SVD view, address scale, breakpoints, and
reset policy.
