# Lab 13: Writing Interface Configs

## Objective

Create or review an interface config for a debug probe.

## Safety

Do not invent VID/PID or pinout values. Use datasheets or known-good configs.

## Tasks

1. Pick an existing interface config.
2. Identify adapter driver selection, transport, VID/PID, layout, and speed.
3. Write a commented draft for a hypothetical related probe.
4. Validate syntax with `-c shutdown` if it does not touch hardware.

## Checkpoints

- Interface configs should not define a specific MCU memory map.
- FTDI configs must be precise about channel/interface selection.

## Deliverables

- Annotated interface config
- Validation command or explanation of why hardware is required

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Review what belongs in an interface file: adapter, USB IDs, layout, transport. |
| 5-11 min | Students annotate an existing interface config line by line. |
| 11-17 min | Identify which values are probe-specific and which are reusable defaults. |
| 17-23 min | Draft a related interface config or review note. |
| 23-27 min | Validate syntax or write the hardware validation boundary. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What information must come from the probe vendor or USB descriptors?
- Why should an interface file not select one specific MCU?
- What is the failure mode of a wrong FTDI channel?

## Exit Ticket

Name three settings that may appear in an interface config.
