# Lab 01: Environment And First Run

## Objective

Install or locate OpenOCD, identify script search paths, and run a safe
first command that exits cleanly.

## Safety

Use the dummy adapter. Do not connect to hardware yet.

## Tasks

1. Locate the OpenOCD binary in your checkout or package artifact.
2. Locate the script directory, usually `tcl` or `share/openocd/scripts`.
3. Run a version command.
4. Run a dummy-adapter shutdown command.
5. Record the binary path, script path, current working directory, and output.

## Commands

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe --version
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -c "adapter driver dummy" -c shutdown
```

## Checkpoints

- OpenOCD starts without needing hardware.
- The command exits on `shutdown`.
- You can explain what `-s`, `-c`, and `adapter driver dummy` do.

## Deliverables

- Command log
- One paragraph explaining the role of the script path
- Any error messages and your diagnosis

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-3 min | Instructor frames OpenOCD as a command-line server plus script engine. |
| 3-7 min | Students locate the binary and script directory in this checkout. |
| 7-12 min | Run `--version`; record version, build date, and binary path. |
| 12-20 min | Run the dummy-adapter shutdown command and annotate each argument. |
| 20-25 min | Pair discussion: what would change if using packaged scripts instead of `tcl`? |
| 25-30 min | Exit ticket and troubleshooting review. |

## Instructor Prompts

- What does OpenOCD need before it can do anything useful?
- Why is a script search path separate from the executable path?
- Why is `adapter driver dummy` a good first command?

## Exit Ticket

Submit one command that starts OpenOCD without hardware and one sentence
explaining why it is safe.
