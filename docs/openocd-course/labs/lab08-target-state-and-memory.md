# Lab 08: Target State And Memory

## Objective

Inspect target state and learn safe memory-read practices.

## Safety

Do not write memory. Read only from known-safe addresses.

## Tasks

1. List the common target states: unknown, running, halted, reset.
2. Find target commands in the OpenOCD manual or via `help`.
3. If hardware is available, halt a target and read a safe memory location.
4. If no hardware is available, write a validation checklist for memory access.

## Example

```text
targets
halt
mdw 0x00000000 4
resume
```

## Checkpoints

- You can explain why memory reads should wait until target attach is proven.
- You can identify a safe memory range from a datasheet or target script.

## Deliverables

- Target state checklist
- Memory-read command log or validation plan

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Review target states and why state matters before memory access. |
| 5-10 min | Students list safe and unsafe target operations. |
| 10-17 min | Hardware track halts and reads known-safe memory; dummy track designs the check. |
| 17-22 min | Interpret success, timeout, bus fault, or unavailable-target errors. |
| 22-27 min | Build a memory-read checklist from datasheet evidence. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why should memory writes be excluded from this lab?
- What does a halted target allow that a running target may not?
- How do you choose a safe address?

## Exit Ticket

State one condition that must be true before reading target memory.
