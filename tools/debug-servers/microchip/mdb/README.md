# Microchip MDB GDB Facade

This folder contains the repo-local debug-server facade for Microchip MPLAB X
MDB.

```text
GDB or Cortex-Debug
  -> 127.0.0.1:3340
  -> mdb_gdb_wrapper.py
  -> MPLAB X mdb.bat command files
  -> PICkit / ICD / Snap / simulator tools selected by MDB
```

## Entry Points

```powershell
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py preflight
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py discover --supported
python .\tools\debug-servers\microchip\mdb\mdb_gdb_wrapper.py server --port 3340
```

The compatibility path still works:

```powershell
python .\tools\support\microchip_mdb_gdb_wrapper.py discover
```

## External Dependencies

- MPLAB X MDB, default Windows path:
  `C:\Program Files\Microchip\MPLABX\v6.25\mplab_platform\bin\mdb.bat`
- A GDB client for the VS Code frontend, commonly `arm-none-eabi-gdb` for the
  current facade transport.
- A Microchip hardware tool visible to MDB, for example PICkit 4, PICkit 5,
  ICD 4, ICD 5, Snap, Atmel-ICE, EDBG, or simulator.

The wrapper does not vendor MPLAB X, MDB jars, device packs, or Microchip USB
drivers.

## Local Vendor Runtime Extraction

To create a local, ignored copy of the MDB runtime from an installed MPLAB X
toolset:

```powershell
.\tools\debug-servers\microchip\mdb\extract-mdb-debug-server.ps1 `
  -Force `
  -IncludeUserModules `
  -IncludePacks `
  -PackName PICkit4_TP,dsPIC30F_DFP
```

This writes:

```text
tools/debug-servers/microchip/mdb/vendor/mplabx-mdb-v6.25/
```

The extracted folder includes `mdb-local.cmd`, `run-mdb-local.ps1`,
`manifest.json`, `mdb.jar`, `mdbcore`, `thirdparty`, DFP packs, user MDB
modules, and the MPLAB-bundled Java runtime. The `vendor/` payload is ignored
by git because it contains proprietary vendor files.

Copying every MPLAB X DFP can exceed local disk capacity. Use `-PackName` to
extract only the tool packs and device-family packs you need. Add more pack
names later, for example `PICkit5_TP`, `ICD5_TP`, `PIC24F-GA-GB_DFP`, or a
specific PIC32 DFP available under `C:\Program Files\Microchip\MPLABX\v6.25\packs`.

## Repo Dependencies

- `docs/usage/microchip-mdb-gdb-facade.md`
- `examples/vscode/microchip-mdb-cortex-debug/`
- `docs/programmers/microchip-pickit-icd.md`

## Current Validation

Read-only discovery on the tested Windows machine reported:

```text
Index 0, tool type pickit4, serial BUR212472292, MPLAB PICkit 4
```

MDB lists connected programmers without a target device. It requires
`Device <part>` before opening the tool and talking to the target controller.
