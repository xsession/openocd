# Lab 24: Capstone Support Package

## Objective

Produce a complete OpenOCD support package for one board, MCU, programmer, or
external programming workflow.

## Safety

All destructive operations require instructor approval and recoverable hardware.

## Required Package

Your capstone must include:

1. support goal and scope;
2. source/provenance and license note;
3. interface, target, board, programmer bridge, or metadata changes;
4. user documentation;
5. support metadata under `support/`;
6. validation commands;
7. known limits;
8. Phase 11-style implementation or hardware gates for anything deferred.

## Suggested Tracks

| Track | Example |
| --- | --- |
| Config-only | New board file composing existing interface and target configs. |
| Delegated tool | External programmer bridge or AVRDUDE workflow expansion. |
| Metadata | Complete Zephyr-style support index for a vendor family. |
| Backend plan | Full import plan for Espressif, WCH, Nuvoton, RISC-V, or AVR protocol support. |
| Hardware validation | Real probe attach and non-destructive target checks. |

## Final Presentation

Prepare a 10-minute presentation:

- problem;
- architecture;
- files changed;
- validation evidence;
- risks and next work.

## Deliverables

- Complete support package
- Command log
- Final presentation outline

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-4 min | Instructor reviews capstone scope and grading criteria. |
| 4-9 min | Students state their chosen track and safety constraints. |
| 9-16 min | Build the file/change checklist for the package. |
| 16-22 min | Define validation evidence and known limits. |
| 22-27 min | Draft the 10-minute presentation outline. |
| 27-30 min | Exit ticket and next-action commitment. |

## Instructor Prompts

- What is the smallest support package that is honest and useful?
- Which evidence is already available, and which evidence is gated?
- What would make this ready for review?

## Exit Ticket

Submit your capstone title, target audience, and first validation command.
