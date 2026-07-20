# PK4 Traceability Matrix

This matrix links observed PK4 firmware facts to the clean-room source artifacts that currently encode or use them.

| Observation | Evidence Source | Clean-room Artifact | Current Purpose |
| --- | --- | --- | --- |
| Boot slot starts at `0x00400000` | `boot.hex`, JAM manifest | `pk4_observed_firmware_profile.h`, `pk4_recovered_project.*`, `pk4_recovery_project.py` | boot slot descriptor and modeled flash window |
| Primary app slot starts at `0x0040C000` | `app.hex`, JAM manifest | `device_state.*`, `pk4_observed_profile.py`, `pk4_recovered_project.*` | primary RI4-facing slot model |
| Secondary app slot starts at `0x00500000` | `app.hex`, JAM manifest | `device_state.*`, `pk4_observed_session.py`, `pk4_recovered_project.*` | CMSIS-DAP/update slot model |
| Primary app reset vector `0x0040E8AD` | `app.hex` vector table | `pk4_observed_firmware_profile.h`, `pk4_observed_profile.py`, recovery project docs/artifacts | execution and manifest metadata |
| Secondary app reset vector `0x00504189` | `app.hex` vector table | `pk4_observed_firmware_profile.h`, `pk4_observed_profile.py`, recovery project docs/artifacts | secondary slot execution metadata |
| `MPLAB PICkit 4 CMSIS-DAP` banner | secondary app string scan | `pk4_observed_profile.py`, `pk4_recovery_project.json`, docs | secondary slot identity |
| Primary-to-secondary slot reference | aligned word scan at `0x00456864` | migration docs, recovery docs | inference that app2 is managed by primary/update logic |
| `0xE000ED00` refs in secondary segment | aligned word scan | migration docs and recovery docs | inference that app2 contains low-level Cortex-M control behavior |

## Use

The matrix is intended to support engineering review and to make it obvious which clean-room modules depend on which observed facts.