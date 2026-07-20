# Operations Guide

This guide summarizes the main operational workflows for the repository.

## Workflow Categories

- asset collection and inspection
- RI4 host-side hardware operations
- simulator-backed debugging
- Zephyr clean-room recovery and probe-scaffold exercises

## Asset Operations

Vendor supported toolpacks and MCU packs:

```powershell
python -m mchp_ri4.asset_collector --all-supported --tools pk4 icd4
```

Export inspection-oriented YAML views:

```powershell
python -m mchp_ri4.asset_storage export-yaml --gzip --source-root vendor\mplabx --output-root vendor\mplabx_yaml_gz
```

## Hardware RI4 Operations

Power a target from a supported tool:

```powershell
python -m mchp_ri4.power_cli --tool pk4 --voltage 5.0
```

Attempt a hardware roundtrip dump/program flow:

```powershell
python -m mchp_ri4.hardware_roundtrip_cli --tool pk4 --pid 0x9012 --family DSPIC30F --processor dsPIC30F5011 --start-address 0x0 --length 0x100 --output dump.hex --power-voltage 5.0
```

## Simulator Operations

The simulator backend is intended for repo-local debug workflows when hardware is unavailable or undesired.

Primary surfaces:

- `mchp_simulator.debug_backend`
- VS Code simulator commands via the backend server

## Zephyr Recovery Operations

Exercise the observed PK4 profile:

```powershell
python -m zephyr_pickit4_replacement.tools.exercise_pk4_status
```

Exercise the observed PK4 RI4 session:

```powershell
python -m zephyr_pickit4_replacement.demo --mode pk4-observed
```

Exercise the clean-room recovery project:

```powershell
python -c "from zephyr_pickit4_replacement.pk4_recovery_project import exercise_pk4_recovery_project; import json; print(json.dumps(exercise_pk4_recovery_project(), indent=2, sort_keys=True))"
```

## Validation Expectations

- Use focused unit tests after changes to protocol, recovery, or session layers.
- Prefer narrow validation close to the edited slice before running broader suites.
- For documentation-only changes, validate machine-readable artifacts and use editor diagnostics to catch broken Markdown or JSON.