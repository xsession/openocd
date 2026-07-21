# Lab 09: Flash Driver Concepts

## Objective

Understand flash banks, flash drivers, work areas, and loaders.

## Safety

No erase or write commands in this lab.

## Tasks

1. Find one flash driver under `src/flash/nor`.
2. Find where flash drivers are registered.
3. Inspect a target script that creates a flash bank.
4. Explain why some flash algorithms need RAM work areas.
5. Write a non-destructive flash validation plan.

## Checkpoints

- You can explain `flash bank`, `flash probe`, erase, write, verify, and
  protect.
- You can explain why flash support should not be guessed.

## Deliverables

- Flash driver notes
- Non-destructive flash safety plan

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-6 min | Explain flash banks, drivers, erase granularity, and RAM loaders. |
| 6-12 min | Students inspect one `src/flash/nor` driver and registration points. |
| 12-17 min | Find a target file that creates a flash bank. |
| 17-23 min | Draft a flash discovery sequence that stops before erase/write. |
| 23-27 min | Discuss why "similar MCU" is not enough evidence for flash writes. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What does `flash probe` prove?
- Why can flash algorithms need target RAM?
- What makes flash testing destructive?

## Exit Ticket

Name one flash command that is discovery-oriented and one that is destructive.
