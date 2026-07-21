# Lab 04: Interface, Target, Board Files

## Objective

Understand the three main runtime configuration file types.

## Safety

Use config-load checks. Do not run flash commands.

## Tasks

1. Inspect one file under `tcl/interface`.
2. Inspect one file under `tcl/target`.
3. Inspect one file under `tcl/board`.
4. Write a table showing which file selects the probe, which file defines the
   chip, and which file composes a usable board setup.
5. Run one target file with the dummy adapter where supported.

## Example

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -c "adapter driver dummy" -f target/ti/tms320f28m35x.cfg -c shutdown
```

## Checkpoints

- Interface files do not define memory maps.
- Target files should not hard-code one physical board.
- Board files should be non-destructive by default.

## Deliverables

- Interface/target/board comparison table
- One successful config-load command or documented reason it cannot load

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Instructor defines interface, target, and board responsibilities. |
| 5-12 min | Students inspect one file of each type. |
| 12-18 min | Fill the comparison table with concrete commands and paths. |
| 18-23 min | Run a dummy-compatible config-load check. |
| 23-27 min | Discuss why automatic programming does not belong in default board files. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What should never be hard-coded in a reusable target file?
- Why does a board file usually `source` other files?
- What makes a config "non-destructive"?

## Exit Ticket

Write one sentence each for interface, target, and board file purpose.
