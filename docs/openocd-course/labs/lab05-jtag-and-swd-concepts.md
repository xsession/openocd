# Lab 05: JTAG And SWD Concepts

## Objective

Learn what OpenOCD means by transport, TAP, DAP, scan chain, and IDCODE.

## Safety

If no hardware is available, complete the concept path. If hardware is
available, run scan-only commands before halt or flash.

## Tasks

1. Define JTAG, SWD, TAP, DAP, IR length, IDCODE, and scan chain.
2. Find a target config that creates a TAP or DAP.
3. Explain what information OpenOCD needs before it can talk to a target.
4. If hardware is available, run `scan_chain` after `init`.

## Example Hardware Command

```powershell
openocd -s .\tcl -f <board.cfg> -c "init; scan_chain; shutdown"
```

## Checkpoints

- You can explain why wrong IR length breaks a JTAG target.
- You can describe how SWD differs from JTAG at a high level.

## Deliverables

- Glossary
- Scan-chain notes or a no-hardware validation plan

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-6 min | Mini-lecture on JTAG scan chains and SWD's two-wire debug model. |
| 6-12 min | Students build the glossary from target config examples. |
| 12-18 min | Trace how a TAP or DAP is created in a real target script. |
| 18-24 min | Hardware track runs `scan_chain`; dummy track writes expected evidence. |
| 24-28 min | Compare syntax success with electrical/protocol success. |
| 28-30 min | Exit ticket. |

## Instructor Prompts

- What does an IDCODE prove, and what does it not prove?
- Why can a scan chain pass while memory access still fails?
- What data would you need from a datasheet?

## Exit Ticket

Define TAP or DAP in your own words and name one command used to inspect it.
