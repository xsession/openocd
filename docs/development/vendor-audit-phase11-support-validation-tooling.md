# Vendor Audit Phase 11: Support Validation Tooling

Phase 11 implements local validation tooling for the Zephyr-style `support/`
metadata tree. The hardware and native backend work identified in Phase 10
remains gated because this workspace does not have the required boards,
debug probes, simulators, or recovery setup for safe integration.

## Implementation

| File | Purpose |
| --- | --- |
| `tools/support/validate-support-metadata.ps1` | Validates support metadata status fields and repository-relative path references. |
| `docs/development/vendor-audit-phase11-support-validation-tooling.md` | Records the Phase 11 implementation batch and validation result. |

## Validator Scope

The validator checks:

- `support/**/*.yml`
- `support/**/*.md`
- status values against the supported vocabulary:
  `integrated`, `delegated`, `experimental`, `deferred`, `blocked`
- repository-relative references that begin with `tcl/`, `docs/`,
  `examples/`, `tools/`, or `support/`

It intentionally avoids a YAML parser dependency so it can run in a fresh
Windows development shell.

## Command

```powershell
.\tools\support\validate-support-metadata.ps1
```

On systems with script execution disabled, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\support\validate-support-metadata.ps1
```

## Result

Phase 11 is complete as a local implementation tooling batch. The remaining
hardware and native backend work moves to Phase 12:

- TI C2000 real attach and flash validation;
- native AVRDUDE protocol ports;
- Espressif newer-chip backend import;
- WCH CH32/WCH-Link backend import;
- Nuvoton `numicro.c` update and M23 aliases;
- RISC-V collaboration backend review;
- Arduino/NDS32 backend decision.
