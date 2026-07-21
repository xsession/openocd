# Lab 06: Reset And Adapter Speed

## Objective

Understand reset configuration, adapter speed, and first-attach strategy.

## Safety

Use low adapter speed first on unfamiliar hardware.

## Tasks

1. Find `adapter speed` usage in existing scripts or docs.
2. Compare reset options in two target or board files.
3. Write a safe first-attach command with low speed.
4. Explain why reset behavior can be board-specific.

## Example

```powershell
openocd -s .\tcl -f board/ti/tms320f28m35x-xds100v3.cfg -c "adapter speed 100" -c init
```

## Checkpoints

- You can explain the risk of assuming reset wiring.
- You can justify a low-speed first attach.

## Deliverables

- Reset strategy note
- Safe first-attach command

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain why reset wiring and debug speed are board-specific. |
| 5-10 min | Students search existing configs for reset and speed settings. |
| 10-16 min | Compare two reset strategies and identify assumptions. |
| 16-22 min | Draft a low-speed first-attach command. |
| 22-27 min | Discuss symptoms of speed too high versus reset misconfiguration. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why is "faster" not always better for first attach?
- What can go wrong if reset is asserted at the wrong time?
- Which reset behavior belongs in a board file?

## Exit Ticket

Write a safe first-attach command with an explicit low adapter speed.
