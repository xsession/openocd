# VS Code Cortex-Debug With OpenOCD MCU Targets

This repository supports Cortex-Debug as a VS Code frontend for OpenOCD-backed
targets beyond classic Cortex-M boards. The reliable pattern is to let OpenOCD
own the probe and target setup, then attach Cortex-Debug through
`servertype: "external"`.

## Supported Shapes

| Target family | Cortex-Debug mode | Required GDB | SVD source |
| --- | --- | --- | --- |
| PIC/dsPIC through PICkit 4 RI4 | External attach | PIC/dsPIC-capable GDB | `svd/microchip/*.svd` |
| AVR through native OpenOCD target support | External attach | `avr-gdb` | Optional or none |
| TI C2000 C28x | External attach | C28x-capable GDB | `svd/ti/tms320f*.svd` |
| Mixed or multi-core MCU | One external attach per OpenOCD GDB port | One GDB per core ISA | One SVD per core |

Cortex-Debug's built-in `openocd` server mode is still best for ordinary
Cortex-M boards. Use `external` for PIC, AVR, C2000 and heterogeneous devices
because those sessions need explicit GDB paths, OpenOCD target scripts, and
sometimes non-ARM reset semantics.

## Start OpenOCD First

Start exactly one OpenOCD process for one physical probe. For multi-core parts,
that one OpenOCD process must create every core target and expose one GDB port
per core.

Examples:

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd.cmd `
  -f programmer/microchip/pickit4-ri4.cfg `
  -c "init"
```

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v2.cmd `
  -f board/ti/launchxl-f28069m-xds100v2.cfg `
  -c "init"
```

```powershell
.\artifacts\windows\openocd-windows-x86_64\openocd-xds100v3.cmd `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c "init; targets"
```

Then attach VS Code with one of the launch configurations from:

```text
tools/vscode/cortex-debug/support/openocd-mcu-launch-examples.json
```

Optional server tasks are available here:

```text
tools/vscode/cortex-debug/support/openocd-server-tasks.json
```

## Multi-Core Rule

Use a VS Code compound launch only for the debug frontends. Do not let every
debug configuration start its own OpenOCD process. The safe model is:

```text
one USB/JTAG probe
one OpenOCD process
one OpenOCD target per core
one GDB port per core
one Cortex-Debug attach configuration per GDB port
```

For heterogeneous devices such as F28M35x, the Cortex-M3 session can use
`arm-none-eabi-gdb`; the C28x session must use a C28x-capable GDB if one is
available. If the installed TI toolchain does not provide GDB for C28x, keep
using CCS or another TI-capable debugger for that core while OpenOCD bring-up
continues.

## Extension Snippets

The vendored Cortex-Debug package includes OpenOCD snippets for:

- `Cortex Debug: OpenOCD External Generic MCU`
- `Cortex Debug: OpenOCD PIC/dsPIC PICkit4`
- `Cortex Debug: OpenOCD AVR`
- `Cortex Debug: OpenOCD C2000`
- `Cortex Debug: OpenOCD Multi-core attach`

These snippets intentionally use `servertype: "external"` and
`overrideAttachCommands`, so they avoid Cortex-M-only assumptions while still
using Cortex-Debug's register, memory, disassembly and peripheral views when
the selected GDB and SVD support the target.

## Address Units

Set `memoryAddressUnitBytes` in each launch configuration so memory and
peripheral reads use the target architecture's address step:

```json
{
  "memoryAddressUnitBytes": 1
}
```

Use `1` for byte-addressed targets such as ARM Cortex-M and AVR. Use `2` for
16-bit word-addressed targets such as TI C2000 C28x and Microchip dsPIC/PIC24.

Cortex-Debug still talks to GDB/OpenOCD in bytes internally. This setting scales
addresses at the debug-adapter boundary, so a displayed C28x or dsPIC address
of `0x1000` maps to byte address `0x2000` when OpenOCD performs the actual
memory read. The legacy Cortex-Debug memory dump also groups 16-bit sessions as
word cells. The peripheral viewer receives the same debug session and SVD
context; keep generated SVD addresses in the same target address units selected
by `memoryAddressUnitBytes`.
