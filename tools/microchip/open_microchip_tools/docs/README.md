# Documentation Index

This directory contains repo-level reference documents for the host-side architecture and integration surfaces.

## Core Architecture

- `system_architecture.md`: repository-wide architecture, boundaries, and subsystem relationships
- `operations_guide.md`: operational workflows across asset, hardware, simulator, and recovery paths
- `troubleshooting.md`: known issues and current operational constraints
- `documentation_style.md`: documentation conventions and clean-room language rules
- `release_readiness.md`: release-quality checklist and review guidance
- `validation_matrix.md`: minimum validation expectations by change type

## Integration Contracts

- `vscode_backend_protocol.md`: JSON-line protocol used between the VS Code extension and the Python backend
- `openocd_integration.md`: OpenOCD bridge contract and operational model

## Related Package Documentation

- `../mchp_ri4/docs/ri4_side_channel.md`: RI4 side/data channel framing and message flow
- `../mchp_ipecmd/docs/README.md`: IPECMD socket protocol package landing page
- `../mchp_ipecmd/docs/ipecmd_socket.md`: IPECMD local socket wire format and operational model
- `../mchp_mdbcore/docs/message_mediator.md`: MDBCore message mediator behavioral contract
- `../mchp_gdbrsp/docs/gdb_rsp.md`: GDB RSP client transport and packet model
- `../zephyr_pickit4_replacement/README.md`: Zephyr scaffold overview
- `../zephyr_pickit4_replacement/docs/pk4_firmware_migration.md`: PK4 firmware migration rationale
- `../zephyr_pickit4_replacement/docs/recovery_project.md`: clean-room recovery-project technical design
- `../zephyr_pickit4_replacement/docs/zephyr_module_architecture.md`: Zephyr internal module boundaries and responsibilities
- `../zephyr_pickit4_replacement/docs/traceability_matrix.md`: observed-fact to source-artifact traceability
- `../zephyr_pickit4_replacement/docs/pk4_combined_manifest.json`: combined machine-readable PK4 recovery/observation manifest