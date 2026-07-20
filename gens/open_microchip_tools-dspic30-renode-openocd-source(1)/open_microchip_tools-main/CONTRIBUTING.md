# Contributing

This repository is developed as a clean-room engineering project. Contributions should preserve that boundary and keep code, tests, artifacts, and documentation aligned.

## Core Expectations

- keep changes scoped to the problem being solved
- validate the edited slice before broadening scope
- update machine-readable artifacts and documentation when behavior or architecture changes
- avoid describing clean-room recovery work as restored proprietary source code

## Change Workflow

1. Identify the smallest concrete failing behavior, file, symbol, or workflow.
2. Make the narrowest plausible change.
3. Run the most focused validation available.
4. Update adjacent docs when the change affects user-visible behavior, architecture, or operational guidance.

## Validation Expectations

- For Python logic, prefer focused `unittest` modules over broad suite runs until the local slice is stable.
- For documentation-only changes, validate machine-readable examples and run editor diagnostics on touched docs.
- For Zephyr C changes, use local diagnostics and the narrowest available build or behavior check given the current SDK environment.

## Clean-room Rules

- Do not add proprietary source code or claim reconstruction of unavailable vendor code.
- Prefer language such as `observed`, `inferred`, `clean-room`, and `behavioral reconstruction`.
- Keep the traceability between observed firmware facts and clean-room source modules explicit.

## Documentation Expectations

When a change affects architecture, protocol surfaces, operational workflows, or constraints, update the relevant docs listed in `docs/README.md`.

Especially relevant documents:

- `docs/system_architecture.md`
- `docs/operations_guide.md`
- `docs/troubleshooting.md`
- `docs/documentation_style.md`
- `zephyr_pickit4_replacement/docs/recovery_project.md`
- `zephyr_pickit4_replacement/docs/traceability_matrix.md`

## Artifact Expectations

If a change affects the PK4 clean-room recovery model, verify whether these artifacts also need updates:

- `zephyr_pickit4_replacement/docs/pk4_recovery_project.json`
- `zephyr_pickit4_replacement/docs/pk4_combined_manifest.json`
- `zephyr_pickit4_replacement/docs/pk4_firmware_observed.json`