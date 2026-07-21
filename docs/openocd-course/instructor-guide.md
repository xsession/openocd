# Instructor Guide

## Teaching Model

Each lab follows this structure:

1. Concept
2. Safety note
3. Preparation
4. Tasks
5. Checkpoints
6. Deliverables
7. 30-minute session plan
8. Instructor prompts
9. Exit ticket

The course works best when students keep a running notebook with commands,
outputs, and short interpretations. Encourage students to explain the boundary
between what OpenOCD did and what the hardware, USB driver, or external tool
did.

## Recommended Setup

At minimum:

- Windows, Linux, or WSL-style shell access;
- this repository checkout;
- a built OpenOCD binary or package artifact;
- Git;
- optional GDB for the chosen target architecture;
- optional hardware debug probe.

For hardware sections, one of these is enough:

- CMSIS-DAP board;
- ST-Link board;
- J-Link board;
- FTDI-based JTAG probe;
- TI XDS100/XDS110;
- AVR programmer usable by AVRDUDE.

## Lab Pacing

| Lab type | Time |
| --- | ---: |
| Intro/dummy labs | 60-90 minutes |
| Hardware labs | 90-150 minutes |
| Audit/documentation labs | 90 minutes |
| Capstone labs | 2-4 hours each |

## Assessment Advice

Grade for reasoning, not only successful hardware output. A strong submission
with no hardware can still pass if it uses dummy validation, records exact
blocked gates, and explains the required hardware evidence.

## Common Failure Modes

| Symptom | Teaching prompt |
| --- | --- |
| `unable to open ftdi device` | Ask which USB interface has WinUSB/libusb binding. |
| Target script fails before `init` | Check missing adapter or transport selection. |
| Flash command unavailable | Check whether a flash bank exists and whether target attach is proven. |
| GDB cannot connect | Check OpenOCD server ports and whether OpenOCD is still running. |
| Config loads with dummy but fails on hardware | Separate syntax success from electrical/protocol success. |

## Capstone Expectations

The final project should include:

- one board/target/programmer or delegated-tool support lane;
- no destructive operation without a written safety gate;
- docs under `docs/`;
- metadata under `support/`;
- exact validation commands;
- a known-limits section;
- a short presentation.
