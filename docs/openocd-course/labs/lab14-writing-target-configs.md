# Lab 14: Writing Target Configs

## Objective

Understand and draft target configuration files.

## Safety

Target scripts may affect reset and attach behavior. Use dummy checks first.

## Tasks

1. Inspect a target config for your chosen architecture.
2. Identify TAP/DAP creation, target creation, work area, reset events, and
   flash banks.
3. Draft a minimal target config for a related MCU.
4. Record which values must come from a datasheet or hardware scan.

## Checkpoints

- Target config values must be evidence-based.
- Work areas should not be guessed.

## Deliverables

- Target config anatomy notes
- Draft target config or review report

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain target scripts as evidence-based MCU descriptions. |
| 5-12 min | Students inspect target creation, TAP/DAP setup, and reset events. |
| 12-18 min | Identify memory map, work area, and flash-bank evidence sources. |
| 18-23 min | Draft a minimal target config or annotate an existing one. |
| 23-27 min | Mark unknown values as gates instead of guesses. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What value would you refuse to invent?
- Why can a work area be dangerous if guessed?
- What is the minimum evidence needed for target creation?

## Exit Ticket

List two target-script fields that must come from a datasheet or hardware scan.
