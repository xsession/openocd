# Static test report: xsession/renode custom-cores

Test date: 2026-07-16

Scope: source-level integration between this repository's Cortex-Debug SVD output
and the public `custom-cores` branch. This was not a full translator execution
test because the execution environment did not contain a built Renode, .NET SDK,
or a dsPIC ELF/GDB toolchain.

## Observed branch features

- `build.sh` includes `dspic33.le` in the Tlib core list.
- `CPU.DSPIC33` reports both Renode and GDB architecture name `dspic33`.
- The GDB register map includes W0-W15, PC, STATUS, TBLPAG, PSVPAG, RCOUNT,
  DCOUNT, CORCON, and DISICNT.
- `dspic30f5011.repl` is an exact platform file and uses byte-addressed SFR
  mappings.
- `dspic33fj128gm802.repl` is present but is not the requested MC802 part.
- Exact platform files for MC802, MC804, and EP128GM604 were absent when tested.

## Test result

The repository's generated minimal dsPIC SVD test fixture placed T1CON and TMR1
at byte addresses 0x100 and 0x102. Both addresses fell inside the Timer1 range in
the branch's exact dsPIC30F5011 platform description: **2/2 covered**.

The validator correctly emitted warnings for:

- empty GDB feature descriptors;
- the interrupt-selection stub;
- three missing exact platform files;
- the GM802/MC802 near-name mismatch.

No structural errors were found in the source snapshot used by the checker.

## Runtime acceptance criteria

A full pass still requires a built custom-cores Renode plus a real XC16-produced
ELF and a dsPIC-capable GDB client. Follow `renode/README.md` and record:

- ELF load and reset PC;
- W-register and PC reads through GDB;
- breakpoint at `main`;
- instruction stepping;
- Cortex-Debug read of a known SFR;
- one modeled peripheral state change;
- absence of translator exceptions.
