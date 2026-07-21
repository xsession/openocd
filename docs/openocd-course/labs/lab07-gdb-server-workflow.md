# Lab 07: GDB Server Workflow

## Objective

Connect GDB to OpenOCD and understand the server ports.

## Safety

Use a known-good board or complete the command-planning path.

## Tasks

1. Identify OpenOCD's default GDB, telnet, and TCL ports.
2. Start OpenOCD for a board or dummy-compatible target.
3. Connect GDB to `localhost:3333`.
4. Run safe commands such as `monitor targets` and `monitor reset halt` only
   when hardware is appropriate.
5. Record how OpenOCD and GDB divide responsibilities.

## Example GDB Commands

```text
target extended-remote localhost:3333
monitor targets
monitor halt
detach
quit
```

## Checkpoints

- You can explain why OpenOCD must keep running while GDB connects.
- You can identify which commands are GDB commands and which are monitor
  commands passed to OpenOCD.

## Deliverables

- GDB session log
- Server-port explanation

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Introduce OpenOCD as a server used by GDB and humans. |
| 5-10 min | Students identify default GDB, telnet, and TCL ports. |
| 10-17 min | Start OpenOCD and connect GDB or write the exact connection plan. |
| 17-22 min | Run safe `monitor` commands and classify command ownership. |
| 22-27 min | Discuss detach, shutdown, and keeping logs from both processes. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Which process talks to the debug probe?
- Why does GDB use `monitor` for OpenOCD commands?
- What happens if OpenOCD exits while GDB is connected?

## Exit Ticket

Name the default GDB port and one `monitor` command.
