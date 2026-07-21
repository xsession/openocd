# Lab 11: USB Probe And Driver Diagnostics

## Objective

Diagnose probe-open errors and OS driver-binding issues.

## Safety

USB diagnostics should not touch target flash.

## Tasks

1. Identify your probe VID/PID and USB interfaces.
2. Run an OpenOCD command that opens or attempts to open the probe.
3. Classify errors as missing device, wrong driver, permission problem, or
   OpenOCD config problem.
4. For Windows FTDI probes, explain interface-specific WinUSB binding.

## Example Error

```text
libusb_open() failed with LIBUSB_ERROR_NOT_FOUND
unable to open ftdi device
```

## Checkpoints

- You can explain why a composite USB device may expose multiple interfaces.
- You can describe when Zadig/libwdi/udev rules are relevant.

## Deliverables

- Probe diagnostic report
- Driver-binding recommendation

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain USB VID/PID, interfaces, kernel drivers, and libusb. |
| 5-10 min | Students inspect probe documentation or OS device information. |
| 10-17 min | Run or analyze a probe-open command and capture the exact error. |
| 17-22 min | Classify the error: missing probe, wrong driver, permission, or config. |
| 22-27 min | Write a fix plan for Windows or Linux. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why might only one interface of a composite device need WinUSB?
- What error suggests driver binding rather than OpenOCD syntax?
- How do permissions differ from missing hardware?

## Exit Ticket

Explain `LIBUSB_ERROR_NOT_FOUND` in one sentence and give one next diagnostic
step.
