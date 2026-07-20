# Troubleshooting Guide

This guide records common operational issues and the current known constraints in the repository.

## Physical PICkit 4 Timeout On Endpoint `0x02`

Symptom:

- RI4 side-channel writes time out when talking to a physical PICkit 4.

Current status:

- This remains the primary real-hardware blocker for full repo-local PK4 session parity.
- The clean-room RI4, observed-session, and recovery-project work is validated mainly through fake transports and host-side models until this is resolved.

## Full YAML Export Exhausts Resources

Symptom:

- `asset_storage export-yaml` fails or produces impractically large outputs.

Recommended action:

- Use `--gzip` for full-tree exports.
- Treat YAML as an inspection surface, not as the runtime storage format.

## Zephyr Include-path Errors In The Editor

Symptom:

- Zephyr headers such as `zephyr/logging/log.h` are reported missing.

Current status:

- This usually reflects local Zephyr SDK or include-path configuration rather than a repo code defect.

## Script Asset Availability Problems

Symptom:

- Hardware or extension flows cannot find the correct `scripts.xml` or compatible target assets.

Recommended action:

- Snapshot toolpacks and DFP assets into `vendor/mplabx/` with `mchp_ri4.asset_collector`.
- Verify that the target family and processor are covered by the collected assets.

## Recovery Project Misunderstanding

Symptom:

- A reader expects the repo to contain restored vendor firmware source.

Clarification:

- The recovery project is a clean-room, source-level compatibility model derived from observed firmware facts.
- It is not decompiled or restored proprietary source code.