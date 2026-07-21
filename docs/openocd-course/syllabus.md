# Syllabus: OpenOCD For Embedded Debug And Programmer Integration

## Course Description

This course teaches OpenOCD as both a user-facing embedded debug tool and a
maintainer-facing integration framework. Students learn how OpenOCD talks to
debug probes, target chips, flash memories, GDB, Tcl scripts, and external
programming ecosystems.

The course uses this repository as the working codebase. It includes labs for
safe command-line use, target configuration, adapter setup, flash workflows,
GDB integration, Windows packaging, AVRDUDE delegation, TI XDS100/XDS110
support metadata, and new-vendor audit practice.

## Learning Outcomes

By the end of the course, students can:

- run OpenOCD safely with local and packaged script paths;
- explain adapter, transport, target, flash, and server boundaries;
- write and validate interface, target, board, and programmer Tcl scripts;
- connect GDB and reason about target state;
- inspect USB probe errors and driver binding problems;
- design non-destructive flash validation plans;
- classify vendor support as config-only, delegated, backend, blocked, or
  deferred;
- create Zephyr-style support metadata for a board, SoC, programmer, or module;
- produce a complete support package with docs, validation logs, and known
  limits.

## Weekly Schedule

| Week | Labs | Theme |
| --- | --- | --- |
| 1 | 01-02 | Environment, OpenOCD mental model |
| 2 | 03-04 | Tcl scripts, interface/target/board files |
| 3 | 05-06 | JTAG/SWD, scan chains, reset |
| 4 | 07-08 | GDB, target state, memory |
| 5 | 09-10 | Flash and safety gates |
| 6 | 11-12 | Adapter drivers, USB, Windows packaging |
| 7 | 13-14 | Vendor audit, support metadata |
| 8 | 15-16 | TI C2000/XDS100/XDS110 lane |
| 9 | 17-18 | AVRDUDE bridge, external programmer delegation |
| 10 | 19-20 | Build, tests, CI, regression strategy |
| 11 | 21-22 | Backend triage, documentation, release artifacts |
| 12 | 23-24 | Capstone design and support package |

## Grading

| Component | Weight |
| --- | ---: |
| Lab notebooks and command logs | 35% |
| Debug/config exercises | 20% |
| Vendor audit report | 15% |
| Final capstone support package | 25% |
| Participation and code review | 5% |

## Required Deliverables

Each lab submission should include:

- command log;
- short explanation of what was tested;
- screenshots or terminal output when useful;
- changed files, if any;
- failure analysis for anything that did not work;
- clear statement of whether hardware was used.

## Hardware Policy

All destructive operations require instructor approval or sacrificial hardware.
If no hardware is available, students complete the dummy/simulation path and
write the validation plan that would be required for real hardware.
