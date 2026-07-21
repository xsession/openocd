# Lab 15: Writing Board Configs

## Objective

Compose interface and target configs into a safe board config.

## Safety

Board configs should be non-destructive by default.

## Tasks

1. Choose one interface config and one target config.
2. Write a board config that sources them.
3. Add board-specific speed or reset settings only when justified.
4. Validate with `-c shutdown`.
5. Write an example command for first attach.

## Checkpoints

- The board config sources reusable pieces.
- It does not automatically erase, unlock, or program.

## Deliverables

- Board config
- First-attach command
- Config-load output

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-4 min | Review board files as composition points. |
| 4-10 min | Students choose reusable interface and target files. |
| 10-16 min | Draft a board config that sources both files. |
| 16-21 min | Add only justified board-specific speed/reset settings. |
| 21-26 min | Run or design a config-load validation. |
| 26-30 min | Exit ticket and peer review. |

## Instructor Prompts

- What makes a board file safe by default?
- What should be left to explicit user commands?
- How does the board file help beginners?

## Exit Ticket

Write one `source` line for an interface file and one for a target file.
