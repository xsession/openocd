# Phase 5 TI Flash Support Result

This records Phase 5 of the vendor-audit checklist for the Texas Instruments
hardware lane.

## Decision

Do not add F28M35x/C2000 JTAG flash banks yet.

Phase 4 proved repository target creation for `tms320f28m35x.c28x`, but real
hardware attach, C28x secondary-TAP routing, halt, register reads, and safe RAM
access are still gated on a powered board and a correctly bound XDS100 probe.
Adding erase/write commands before that point would create a dangerous false
promise.

| Item | Phase 5 decision |
| --- | --- |
| First flash target | F28M35x C28x flash path |
| Existing reusable JTAG driver | None confirmed |
| Existing related driver | `ti_f28004x_serial`, for TI SCI boot serial programming only |
| New NOR driver | Deferred |
| RAM loader | Deferred |
| Flash banks in F28M35x config | None |
| Flash examples | None |

## Existing Driver Review

The tree already contains `src/flash/nor/ti_f28004x_serial.c`.

That driver is registered in:

```text
src/flash/nor/Makefile.am
src/flash/nor/driver.h
src/flash/nor/drivers.c
```

It is intentionally not a reusable F28M35x JTAG flash driver:

- It shells out to TI's external `serial_flash_programmer.exe`.
- It expects SCI boot-format text files.
- Its generic `erase` and `write` callbacks return unsupported-operation
  errors.
- It is scoped to the F28004x serial boot flow, not XDS100 JTAG debug access.

## Local Validation

The existing serial driver registration was checked with a dummy target and a
non-destructive pseudo-bank:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl `
  -c "adapter driver dummy" `
  -f target/ti/tms320f280049.cfg `
  -c "flash bank f280049.serial ti_f28004x_serial 0 0x40000 2 2 tms320f280049.cpu COM19" `
  -c "flash banks" `
  -c shutdown
```

Result:

```text
#0 : f280049.serial (ti_f28004x_serial) at 0x00000000, size 0x00040000, buswidth 2, chipwidth 2
```

This proves the existing serial driver is registered and parsable.  It does not
prove F28M35x JTAG flash support.

## F28M35x Flash Acceptance Gate

Before any F28M35x flash bank or driver is added, complete these hardware checks
on a recoverable board:

```text
init
scan_chain
c2000_icepick_read_idcode
c2000_icepick_read_code
c2000_icepick_scan_sdtaps
targets
halt
reg
mdw <known_safe_ram_address> 4
```

Only after those pass:

- confirm the exact F28M35x part number;
- confirm flash bank base addresses, sector layout, and security behavior from
  the matching data sheet or technical reference manual;
- identify whether a RAM-resident flash algorithm is required;
- test on sacrificial or recoverable hardware first.

## Deferred Flash Test Matrix

When the target attach and memory-read gates pass, Phase 5 should be reopened
for destructive validation:

| Test | Required proof |
| --- | --- |
| Probe | `flash probe 0` reports the exact device or variant. |
| Erase | Sector erase succeeds and blank-check reports erased state. |
| Write | A small image writes to a known safe flash sector. |
| Verify | `verify_image` or equivalent confirms written contents. |
| Protect | Protected sector behavior is detected and reported clearly. |
| Unlock | Unlock is tested only if the recovery path is known. |
| Alignment | Wrong-size or wrong-alignment writes fail safely. |

## Phase 5 Conclusion

Phase 5 is complete as a safe flash-support decision:

- No existing OpenOCD JTAG flash driver was confirmed reusable for F28M35x.
- The related F28004x serial helper was reviewed and left scoped to serial boot
  programming.
- No F28M35x flash bank, flash example, erase command, or RAM loader was added.
- The exact hardware gate for future flash work is documented.
