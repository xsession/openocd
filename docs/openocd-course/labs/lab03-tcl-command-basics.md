# Lab 03: Tcl Command Basics

## Objective

Learn how OpenOCD Tcl commands are loaded, invoked, and validated.

## Safety

Use dummy commands only.

## Tasks

1. Create a scratch Tcl config outside the course directory or in your lab
   notebook area.
2. Add `puts` messages and simple variable assignments.
3. Run OpenOCD with `-f <your-file>` and `-c shutdown`.
4. Add a deliberate Tcl error, observe the failure, then fix it.
5. Explain how OpenOCD command order affects configuration.

## Example

```tcl
set COURSE_LAB 3
puts "Lab $COURSE_LAB config loaded"
adapter driver dummy
```

## Checkpoints

- Your config prints a message.
- A syntax error fails before hardware access.
- You can explain the difference between `-f` and `-c`.

## Deliverables

- Minimal Tcl config
- Command log
- Short explanation of command ordering

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain that OpenOCD config files are Tcl scripts with OpenOCD commands. |
| 5-11 min | Students create a minimal script with `puts` and `adapter driver dummy`. |
| 11-16 min | Run the script and record output. |
| 16-21 min | Introduce a deliberate syntax or unknown-command error. |
| 21-26 min | Fix the script and compare failure location versus runtime behavior. |
| 26-30 min | Exit ticket. |

## Instructor Prompts

- What is evaluated first: `-f` files or later `-c` commands?
- How can a config fail before any probe is opened?
- When should a script print helpful status?

## Exit Ticket

Show one Tcl line that configures OpenOCD and one Tcl line that only prints
information.
