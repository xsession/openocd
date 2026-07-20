# Validation Matrix

This matrix maps common change types to the minimum expected validation scope.

| Change Type | Minimum Validation | Typical Supporting Checks |
| --- | --- | --- |
| Python protocol logic | focused `unittest` module | editor diagnostics, related demo command |
| Zephyr C logic | local diagnostics and nearest behavior check | focused host mirror tests, docs update |
| Machine-readable artifact | parse/read artifact directly | traceability and docs alignment |
| Documentation-only | editor diagnostics on touched docs | validate referenced commands where practical |
| PK4 recovery model | focused recovery/session/profile tests | manifest parse, docs and traceability review |

## Current High-value Validation Paths

- `tests.test_pk4_observed_profile`
- `tests.test_zephyr_pk4_observed_session`
- `tests.test_zephyr_demo`
- `tests.test_pk4_recovery_project`

## Operational Checks

When a docs change introduces or updates a command example, prefer running at least one representative command from the edited set.
## Renode custom-core backend

| Capability | Automated fake-RSP test | Covered by real-Renode E2E harness | Physical PK4 required |
|---|---:|---:|---:|
| Connect/capability discovery | yes | yes | no |
| PC read/write | yes | yes | no |
| Memory read/write | yes | yes | no |
| Erase emulated flash | yes | yes | no |
| Program Intel HEX | yes | yes | no |
| Standard OpenOCD NOR bank registration | static/installer/Tcl tests | yes | no |
| `flash erase_sector` / `flash write_image` / `verify_image` | callback and harness tests | yes | no |
| Verify Intel HEX and mismatch reporting | yes | yes | no |
| Single-step | yes | yes | no |
| Asynchronous run/halt | yes | yes | no |
| Hardware breakpoint add/remove | yes | yes | no |
| Read/write/access watchpoints | yes | yes | no |
| Machine reset and reset-PC restore | yes | yes | no |
| RI4 device-pack script execution | not applicable | not applicable | yes |
| Electrical ICSP timing/voltage behavior | not applicable | not applicable | yes |

The repository's unit suite exercises the complete bridge contract against a
stateful fake Renode GDB server. The “E2E harness” column means the operation is
implemented in `renode/run_openocd_e2e.py`; it does not claim that the real
Renode executable was run in every development environment. Use that script as
the qualification harness for a built `xsession/renode:custom-cores` checkout
and an OpenOCD binary compiled with this overlay.
