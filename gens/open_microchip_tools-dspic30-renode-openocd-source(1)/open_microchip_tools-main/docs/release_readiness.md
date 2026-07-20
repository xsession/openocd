# Release Readiness Guide

This guide summarizes the material expected for a high-quality internal release of the repository.

## Required Technical Inputs

- focused tests for changed behavior pass
- machine-readable artifacts affected by the change are updated
- architecture and operational docs reflect the current implementation

## Required Documentation Inputs

- repo overview is still accurate
- subsystem docs are aligned with user-visible behavior
- current blockers are documented rather than hidden
- clean-room language remains consistent

## Release Checklist

### Code and Validation

- run the narrowest relevant unit tests for the changed modules
- verify JSON artifacts parse successfully
- check editor diagnostics for touched source and docs

### Documentation and Artifacts

- update `docs/README.md` if new docs are added
- update subsystem indexes if new artifacts are added
- update traceability documents when observed PK4 facts or recovery mappings change

### Operational Review

- confirm documented commands still execute
- confirm known hardware blockers are still stated correctly
- confirm asset-vendoring guidance still matches the current collector/storage behavior

## Special Notes For PK4 Recovery Changes

When the observed PK4 profile or recovery project changes, review all of the following together:

- `zephyr_pickit4_replacement/docs/pk4_firmware_migration.md`
- `zephyr_pickit4_replacement/docs/recovery_project.md`
- `zephyr_pickit4_replacement/docs/traceability_matrix.md`
- `zephyr_pickit4_replacement/docs/pk4_recovery_project.json`
- `zephyr_pickit4_replacement/docs/pk4_combined_manifest.json`