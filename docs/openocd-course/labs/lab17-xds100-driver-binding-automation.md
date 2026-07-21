# Lab 17: XDS100 Driver Binding Automation

## Objective

Understand Windows driver binding for FTDI-based XDS100 probes and how helper
scripts should guide users.

## Safety

Do not change driver bindings on shared machines without permission.

## Tasks

1. Read the XDS100 programmer docs.
2. Inspect `tools/ti/windows/openocd-xds100v3.ps1`.
3. Explain why FTDI `MI_00` is bound to WinUSB and `MI_01` may remain UART.
4. Write a user-friendly driver-install checklist.
5. Record how to detect the common `LIBUSB_ERROR_NOT_FOUND` failure.

## Checkpoints

- You can explain the difference between installing OpenOCD and binding a USB
  interface driver.
- You can write a recovery note for wrong driver binding.

## Deliverables

- Driver-install checklist
- Failure-diagnosis table

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain composite FTDI probes and interface-specific driver binding. |
| 5-12 min | Students inspect the XDS100 PowerShell wrapper and docs. |
| 12-18 min | Trace how helper scripts guide or automate WinUSB installation. |
| 18-23 min | Write a beginner-friendly checklist for a failed probe open. |
| 23-27 min | Classify common errors and recovery steps. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why can `MI_00` and `MI_01` need different drivers?
- What should automation do before making driver changes?
- How should a helper explain failure without hiding the real error?

## Exit Ticket

Write the first two questions you ask when XDS100 fails to open.
