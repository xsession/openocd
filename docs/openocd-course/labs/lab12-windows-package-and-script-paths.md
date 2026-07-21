# Lab 12: Windows Package And Script Paths

## Objective

Validate a packaged OpenOCD tree and understand script lookup.

## Safety

Use `-c shutdown` and config-load checks.

## Tasks

1. Locate `artifacts/windows/openocd-windows-x86_64`.
2. Identify `bin/openocd.exe` and `share/openocd/scripts`.
3. Run a config-load command using the packaged script path.
4. Compare packaged scripts with source-tree `tcl`.
5. Record how wrapper scripts choose script paths.

## Example

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts `
  -f board/ti/tms320f28m35x-xds100v3.cfg `
  -c shutdown
```

## Checkpoints

- Packaged script path works.
- You can explain when to use source `tcl` versus packaged scripts.

## Deliverables

- Package validation log
- Script path explanation

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Show package layout: `bin` versus `share/openocd/scripts`. |
| 5-10 min | Students locate packaged OpenOCD and packaged scripts. |
| 10-17 min | Run a packaged config-load check. |
| 17-22 min | Compare source-tree `tcl` and packaged script paths. |
| 22-27 min | Discuss wrapper scripts and why `-s` must be unambiguous. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why can a script work from source but fail from a package?
- What should a wrapper do when it cannot find scripts?
- Why should validation use the same package users will run?

## Exit Ticket

Write one command that uses the packaged `share/openocd/scripts` path.
