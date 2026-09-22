# Microchip MDB Cortex-Debug Example

This example connects Cortex-Debug to Microchip MPLAB X MDB through the local
GDB facade in `tools/debug-servers/microchip/mdb/mdb_gdb_wrapper.py`.

It is useful when a Microchip device/tool pair works in MDB but is not yet a
native OpenOCD target.

## Files

| File | Purpose |
| --- | --- |
| `tasks.json` | Starts the MDB facade on `localhost:3340`. |
| `launch.json` | Attaches Cortex-Debug to the facade and sends MDB monitor commands. |

Copy these into a firmware workspace's `.vscode` directory, then adjust:

- `--device`
- `--hwtool`
- `executable`
- `gdbPath`

## First Test

From the OpenOCD repository root:

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py `
  --mdb "C:\Program Files\Microchip\MPLABX\v6.25\mplab_platform\bin\mdb.bat" `
  preflight
```

Then in VS Code:

1. Run task `Microchip MDB: start GDB facade`.
2. Launch `Microchip MDB: monitor through GDB facade`.

The launch sends:

```text
monitor discover
monitor supported
```

On the tested workstation, MDB reported one connected programmer:

```text
Index 0, tool type pickit4, serial BUR212472292, MPLAB PICkit 4
```

MDB cannot identify the target controller from the programmer alone. It requires
the expected part name through `Device <part>` before it will open the tool and
talk to the target board.

## Notes

This is a GDB-compatible facade over MDB command files. It is not a full native
OpenOCD target implementation and it does not make ARM GDB understand PIC or
dsPIC registers. Keep `--enable-control` disabled until basic monitor commands
work with the selected device and tool.
