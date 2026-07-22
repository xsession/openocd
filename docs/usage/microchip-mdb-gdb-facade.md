# Microchip MDB GDB Facade

`tools/debug-servers/microchip/mdb/mdb_gdb_wrapper.py` exposes a small GDB Remote Serial
Protocol endpoint backed by Microchip MPLAB X MDB:

```text
GDB or Cortex-Debug -> MDB facade 127.0.0.1:3340 -> mdb.bat command files -> MPLAB X tools
```

MDB is not OpenOCD and is not a native GDB server. The facade exists so a
GDB-fronted workflow can attach, stay stopped, and send `monitor ...` commands
to MDB from the same style of VS Code setup used for OpenOCD external servers.

## Preflight

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py `
  --mdb "C:\Program Files\Microchip\MPLABX\v6.25\mplab_platform\bin\mdb.bat" `
  preflight
```

Expected result: MDB prints its command classes, including `deviceandtool`,
`running`, `data`, `breakpoints`, and `programming`.

## Run MDB Commands Directly

List connected Microchip tools:

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py discover --supported
```

Select a device and tool, then inspect MDB state:

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py command `
  --device PIC32MX360F512L `
  --hwtool PICkit4 `
  "help running" `
  "info breakpoints"
```

The wrapper creates a temporary MDB command file for each transaction. It does
not keep an interactive MDB process alive.

## Start The GDB Facade

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py server `
  --device PIC32MX360F512L `
  --hwtool PICkit4 `
  --listen-host 127.0.0.1 `
  --port 3340
```

Then connect a GDB client:

```powershell
arm-none-eabi-gdb -nx -q `
  -ex "target extended-remote 127.0.0.1:3340" `
  -ex "monitor discover" `
  -ex "monitor Hwtool" `
  -ex "disconnect" `
  -ex "quit"
```

Useful monitor aliases:

```text
monitor discover   -> MDB Hwtool
monitor tools      -> MDB Hwtool
monitor supported  -> MDB Hwtool supported
```

MDB can list connected programmers without knowing the target part. To open the
tool and communicate with the target controller, MDB requires an explicit
`Device <part>` first.

## Control Translation

By default, the facade only forwards explicit `monitor ...` commands. Add
`--enable-control` if you want GDB packets to call MDB commands:

```text
GDB continue -> MDB Continue
GDB step     -> MDB Stepi 1
GDB Ctrl-C   -> MDB Halt
GDB Z0/z0    -> MDB break/delete
```

This mode touches the selected debugger and target. Keep it off while you are
only checking that VS Code can connect.

## Cortex-Debug

Use `servertype: "external"` and attach to `127.0.0.1:3340`. The facade returns
a minimal ARM-looking target description so Cortex-Debug and ordinary ARM GDB
can attach even when MDB is controlling a PIC, dsPIC, AVR, or SAM target.

That compatibility target description is only a transport shim. Real
source-level debugging still depends on the selected Microchip architecture,
compiler output, MDB command support, and hardware tool.

Example files:

```text
examples/vscode/microchip-mdb-cortex-debug/
```

## OpenOCD Relationship

Use native OpenOCD targets when the probe exposes a standard debug transport or
when this tree has native Microchip support, such as PICkit 4/ICD 4 RI4 work.

Use the MDB facade when the only working debug path for a device/tool pair is
Microchip MDB. In that case OpenOCD does not own the target during the MDB
session; the facade simply gives GDB/Cortex-Debug a familiar attach surface.
