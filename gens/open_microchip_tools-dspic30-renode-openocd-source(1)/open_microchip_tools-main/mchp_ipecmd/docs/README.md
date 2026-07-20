# mchp_ipecmd docs

This package documents the clean-room local socket surface used to emulate the behavioral contract of Microchip IPE command helpers.

## Documents

- Protocol reference: `ipecmd_socket.md`
- Diagrams: `diagrams/ipecmd_component.svg`, `diagrams/ipecmd_sequence.svg`

## Role In The Repo

`mchp_ipecmd` is the simplest transport-facing package in the workspace. It gives the repo a runnable local socket protocol surface for IPE-style flows while the other packages focus on RI4, debugger, simulator, and firmware work.
