# Lab 16: TI C2000/XDS100 Case Study

## Objective

Study the TI C2000/XDS100/XDS110 support lane in this repository.

## Safety

Do not run flash commands. Treat C2000 flash as deferred until hardware gates
are met.

## Tasks

1. Read `docs/targets/ti-c2000-support.md`.
2. Read `docs/programmers/ti-xds100.md`.
3. Inspect one C2000 board file under `tcl/board/ti`.
4. Run a package config-load check.
5. Summarize which parts are integrated and which remain hardware-gated.

## Example

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c shutdown
```

## Deliverables

- Support-status note
- Known-limits summary

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Introduce the TI C2000/XDS100 lane and its support boundaries. |
| 5-11 min | Students inspect one XDS100 board file and one example file. |
| 11-17 min | Run the package config-load command or analyze recorded output. |
| 17-22 min | Fill a table: integrated, experimental, blocked, deferred. |
| 22-27 min | Discuss why flash and C28x operation tests remain hardware-gated. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Which part of XDS100 support is already integrated?
- What did dummy/config-load validation prove?
- What does it not prove about real C28x debugging?

## Exit Ticket

State one completed TI lane item and one remaining hardware gate.
