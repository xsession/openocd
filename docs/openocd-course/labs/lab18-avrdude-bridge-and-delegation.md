# Lab 18: AVRDUDE Bridge And Delegation

## Objective

Use the AVRDUDE bridge and understand delegated support versus native OpenOCD
support.

## Safety

Use `avrdude dry_run on` unless using approved AVR hardware.

## Tasks

1. Read `docs/programmers/avrdude.md`.
2. Run `avrdude help` through OpenOCD.
3. Build a dry-run command for `arduino` or `usbasp`.
4. Explain which catalog comes from AVRDUDE and which command surface comes
   from OpenOCD.
5. Identify why fuse and lock-bit operations need extra care.

## Example

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f programmer/avrdude/common.tcl `
  -c "avrdude dry_run on" `
  -c "avrdude programmer usbasp" `
  -c "avrdude part atmega328p" `
  -c "avrdude command read flash flash.hex i" `
  -c shutdown
```

## Deliverables

- Dry-run proof
- Delegated-versus-native explanation

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Define delegated support versus native OpenOCD backend support. |
| 5-10 min | Students read the AVRDUDE bridge command map. |
| 10-17 min | Run `avrdude help` and one dry-run command through OpenOCD. |
| 17-22 min | Trace which arguments become AVRDUDE CLI options. |
| 22-27 min | Discuss fuse/lock-bit risk and why `raw` is explicit. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Which tool owns the MCU/programmer catalog?
- What does OpenOCD add in this delegated workflow?
- Why is delegated support still valuable?

## Exit Ticket

Write the generated AVRDUDE command from your dry-run output.
