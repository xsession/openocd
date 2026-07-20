# PIC18 Stub Probe Path

This Zephyr subproject now includes a clean-room development path for one concrete family: `PIC18`.

Instead of emulating MPLAB RI4 script bytecode, the repo can generate a Zephyr-specific `scripts.xml` where each named script maps to a tiny custom opcode understood by the firmware stub executor.

## Supported Named Scripts

- `EnterDebugMode`
- `GetPC`
- `SetPC`
- `Run`
- `Halt`
- `SingleStep`
- `EraseChip`
- `WriteProgmem`
- `ReadProgmem`
- `EnterTMOD_LV`
- `ExitTMOD`

Other generated names are accepted as no-op success paths so host-side family negotiation can continue during bring-up.

## Where This Fits Now

The PIC18 stub path is still useful, but it is no longer the only documentation anchor for the Zephyr subproject. It now sits alongside the PK4-observed session and recovered-project path:

- PIC18 stub path: family-oriented bring-up and generic RI4 session testing
- PK4 observed path: PK4-compatible slot/status/session modeling
- recovery-project path: clean-room source-level project structure derived from observed boot/app images

## Generate Stub Assets

```powershell
python -m zephyr_pickit4_replacement.tools.gen_stub_scripts_xml --family PIC18 --processor PIC18F_STUB --output .\scripts.xml
```

That file can be used with `NamedScriptSession.open_usb()` or the VS Code hardware session flow.

## Firmware Behavior

- `GetPC` returns the mock device-state PC in little-endian format.
- `SetPC` updates the mock PC from the first `u32` parameter.
- `SingleStep` increments the PC by 2 bytes.
- `WriteProgmem` writes the RI4 download payload into mock flash at the requested address.
- `ReadProgmem` returns bytes from mock flash at the requested address.
- `EraseChip` resets mock flash to `0xFF`.

This gives the repo a fully clean-room, repo-local programming/debug path for firmware bring-up, even though real PIC electrical control is still not implemented.

## Repo-Local Demo

```powershell
python -m zephyr_pickit4_replacement.demo
```

That command auto-generates a temporary PIC18 stub `scripts.xml`, opens a repo-local `NamedScriptSession` backed by the fake stub probe, performs a small debug/program/readback cycle, prints JSON output, and removes the temporary XML file.

For the second modeled family path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family ARM_MPU --processor ATSAME70_STUB
```

For a PE-style path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family PIC32MZ --processor PIC32MZ2048EFH_STUB
```

For a dsPIC DE-style path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family DSPIC33A --processor DSPIC33AK128MC106_STUB
```

For an AVR prog-mode path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family AVR --processor ATMEGA4809_STUB
```

For a PIC16 enhanced path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family PIC16Enhanced --processor PIC16F1509_STUB
```

For a dsPIC30F5011 path, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family DSPIC30F --processor DSPIC30F5011_STUB
```

For dsPIC33 PE-style paths, run:

```powershell
python -m zephyr_pickit4_replacement.demo --family DSPIC33FJ --processor DSPIC33FJ256GP710A_STUB
python -m zephyr_pickit4_replacement.demo --family DSPIC33EP --processor DSPIC33EP512MU810_STUB
```