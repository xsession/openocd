# Lab 10: Safe Flash Workflow

## Objective

Design a flash workflow that separates discovery from destructive operations.

## Safety

Do not erase, unlock, or write unless using approved recoverable hardware.

## Tasks

1. Write a staged flash workflow: config load, attach, halt, probe, backup,
   erase, write, verify.
2. Mark which steps are safe and which are destructive.
3. Add rollback or recovery steps.
4. If approved hardware is available, run only discovery steps.

## Example Stages

```text
openocd -f <board.cfg> -c "init; targets; shutdown"
openocd -f <board.cfg> -c "init; halt; flash banks; shutdown"
```

## Checkpoints

- Flash probe must happen before write.
- Backup and recovery matter before erase.

## Deliverables

- Safe flash workflow script
- Risk table

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Review destructive versus non-destructive flash operations. |
| 5-11 min | Students sequence attach, halt, probe, backup, erase, write, verify. |
| 11-17 min | Mark each step as safe, risky, or destructive. |
| 17-23 min | Add recovery steps for failed write, protected sector, or wrong image. |
| 23-27 min | Peer review workflows for missing safety gates. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What is the earliest point where the workflow can stop safely?
- Why should backup happen before erase?
- What evidence is needed before unlocking protection?

## Exit Ticket

List the first three commands you would run before any flash write.
