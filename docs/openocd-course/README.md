# OpenOCD University Course

This directory contains a 24-lab university course for learning OpenOCD from
first principles through advanced target, programmer, flash, and vendor-support
integration work.

The course is designed for a 12-week semester with two labs per week, or a
compressed 6-week studio with four labs per week. Labs are written so students
can begin with `dummy` adapter workflows and later move to real hardware.
Every lab includes a detailed 30-minute session plan with timing, instructor
prompts, student work, and an exit ticket.

## Course Goals

Students who complete the course should be able to:

- explain OpenOCD's adapter, transport, target, flash, server, and Tcl layers;
- run OpenOCD with safe config-load and dry-run commands;
- connect GDB to OpenOCD and debug a small firmware image;
- understand JTAG/SWD scan chains, reset behavior, and target state;
- read and write OpenOCD interface, target, board, and programmer scripts;
- diagnose USB driver, adapter, target, and flash errors;
- package and validate OpenOCD changes on Windows/Linux-style workflows;
- audit new vendor support without copying whole forks blindly;
- document support status with clear hardware and safety gates.

## Directory Map

```text
docs/openocd-course/
├── README.md
├── syllabus.md
├── lab-index.md
├── instructor-guide.md
├── assessment-rubric.md
└── labs/
    ├── lab01-environment-and-first-run.md
    ├── ...
    └── lab24-capstone-support-package.md
```

## Recommended Prerequisites

- Basic C programming
- Basic command-line usage
- Some exposure to embedded systems
- Optional but helpful: Git, Make/CMake, GDB, USB device basics

## Hardware Tracks

The labs are written with three tracks:

| Track | Use when | Notes |
| --- | --- | --- |
| Simulation/dummy | No hardware is available | Uses `adapter driver dummy`, config-load tests, and dry-run workflows. |
| Common ARM board | A CMSIS-DAP, ST-Link, J-Link, or FTDI board is available | Use local board files where possible. |
| Vendor integration | TI XDS100/XDS110, AVRDUDE, or another programmer is available | Uses the support metadata and vendor-audit flow in this repository. |

## Safety Rules

1. Never run erase, unlock, fuse, lock-bit, or write commands on shared or
   valuable hardware until the lab explicitly says to do so.
2. Prefer `-c shutdown`, `adapter driver dummy`, and dry-run commands during
   script development.
3. Record every command that touches hardware.
4. Treat unknown flash, security, and reset behavior as destructive until proven
   otherwise.
5. For Windows USB probes, verify driver binding before blaming OpenOCD.

## Quick Start

Start with:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -c "adapter driver dummy" -c shutdown
```

Then open [lab-index.md](lab-index.md) and begin Lab 01.
