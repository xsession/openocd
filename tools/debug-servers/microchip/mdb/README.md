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
