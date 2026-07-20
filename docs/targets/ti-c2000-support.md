# TI C2000 / C28x support

This repository now contains two C2000 support layers:

1. `target/ti/c2000-icepick-scan.cfg` for the visible TI ICEPick-C router TAP.
2. `src/target/c28x.c` / `src/target/c28x.h` for a real OpenOCD `c28x` target type.

The target files for `tms320f28069`, `tms320f280049`, and `tms320f28m35x`
source the ICEPick helper and create a C28x target instance:

```text
target/ti/tms320f28069.cfg
target/ti/tms320f280049.cfg
target/ti/tms320f28m35x.cfg
```

Convenience board files are also provided:

```text
board/ti/launchxl-f28069m-xds100v2.cfg
board/ti/tms320f28069-xds110.cfg
board/ti/tms320f280049-xds110.cfg
board/ti/tms320f28m35x-xds110.cfg
```

## Implemented C28x backend features

The `c28x` backend implements the normal OpenOCD target interface:

- target registration as `-type c28x`
- target creation, initialization, examination, and teardown
- architecture state reporting
- poll, halt, resume, and single-step entry points
- reset, reset-halt, and soft-reset-halt entry points
- GDB architecture hook, defaulting to `c28x`
- GDB register-list hook
- C28x register cache in CCS/TI register-ID order: PC, SP, ACC, P, XT, ST0,
  ST1, XAR0-XAR7, IER, IFR, DP, DBGIER, RPC, and RPTC
- register get/set dispatch through the target transport layer
- byte/halfword/word memory read/write conversion for a 16-bit word-addressed
  C28x memory model
- hardware breakpoint and watchpoint bookkeeping
- address/data bit reporting: 32-bit addresses, 16-bit target data bus
- low-level Tcl commands for transport bring-up and JTAG investigation

The command group is available after `init`:

```text
c28x info
c28x device [name]
c28x gel_file [path]
c28x procid [value]
c28x icepick_port [port]
c28x xds110 [memread memwrite]
c28x regids [core|debug|mapped|all]
c28x transport enable|disable
c28x ir <name> [value]
c28x status_format <bits> <halt-mask> <run-mask>
c28x raw_ir <value>
c28x raw_dr <bits> [value]
c28x idcode
c28x status
c28x gdb_arch [arch]
```

Supported `c28x ir` names:

```text
idcode status halt resume step reg_read reg_write mem_read16 mem_write16
bp_write wp_write bypass
```

## CCS-derived metadata

The C28x register cache and diagnostic register table are derived from TI CCS
`ccs_base/common/targetdb/cpus/c28xx.xml` and
`ccs_base/common/targetdb/drivers/TI_reg_ids/TMS320C28XX_regids.xml`.  The
three supplied target files also annotate each target with CCS targetdb metadata:

| Target file | CCS device | C28x ProcID | ICEPick-C C28x port | GEL file |
| --- | --- | --- | --- | --- |
| `tms320f28069.cfg` | `TMS320F28069` | `0x5000A3F8` | direct/unset in CCS XML | `../../emulation/gel/f28069.gel` |
| `tms320f280049.cfg` | `TMS320F280049` | `0x5000A3F8` | `0x10` | `../../emulation/gel/f280049.gel` |
| `tms320f28m35x.cfg` | `F28M35x-C28x` | `0x5000A3F8` | `0x11` | `../../emulation/gel/f28m35h52c1_c28.gel` |

The XDS110 binary driver also contains C28x memory command names and command
IDs.  Disassembly of `ccs_base/common/uscif/jscxds110.dll` shows
`C28X_MEMREAD = 0x33` and `C28X_MEMWRITE = 0x34`; the backend stores these
for diagnostics with `c28x xds110`.

## Transport boundary

The backend fails closed by default.  The C28x architectural state is public,
but the private C28x debug-TAP packet encoding used by TI CCS/XDS tools is not
published in the public C28x CPU guide.  Therefore the backend does not invent
hard-coded halt/register/memory opcodes.  A board file, lab script, or future
silicon-specific driver must provide verified IR values before enabling the
transport:

```text
c28x ir status 0x...
c28x ir halt 0x...
c28x ir resume 0x...
c28x ir step 0x...
c28x ir reg_read 0x...
c28x ir reg_write 0x...
c28x ir mem_read16 0x...
c28x ir mem_write16 0x...
c28x status_format 32 0x1 0x2
c28x transport enable
```

This is intentional safety behavior.  C2000 flash, security, and emulation
register mistakes can lock or disturb real devices.  Once verified transport
opcodes are available, the existing backend code paths already route halt,
resume, step, register, memory, breakpoint, and watchpoint operations through
that transport.

## ICEPick-C discovery commands

The ICEPick helper still exposes the router-level commands:

```text
c2000_icepick_connect
c2000_icepick_read_idcode
c2000_icepick_read_code
c2000_icepick_router_read <register>
c2000_icepick_router_write <register> <24-bit-value>
c2000_icepick_scan_sdtaps
c2000_support_status
```

Use those commands first on unknown hardware to discover the visible router and
secondary TAP topology.

## Build validation performed

The target library and executable were built locally with:

```text
./bootstrap
./configure --disable-werror --enable-dummy --enable-internal-jimtcl
make -j8 src/target/libtarget.la
make -j8 src/openocd
```

Smoke tests loaded all three target configs with the dummy JTAG adapter and
confirmed that a C28x target is created and the `c28x info` command works.

## Remaining hardware validation

The OpenOCD backend is now present and buildable, but real C28x silicon still
needs verified private transport opcodes or a TI-published debug-TAP packet
specification.  Without those values, full hardware halt/resume/register/memory
operations correctly return an error instead of sending guessed JTAG commands.

## CCS-native GTI/TRG metadata

The C28x backend includes CCS-derived native operation metadata recovered from the user-supplied CCS package. The values are exposed for inspection with:

```tcl
c28x gti all
```

Recovered operation IDs include register read/write (`0x05`/`0x06`), run/step/halt (`0x0d`/`0x0e`/`0x0f`), block memory read/write (`0x41`/`0x42`), and status/preflight (`0x5a`). XDS110 C28x memory command IDs are recorded as `C28X_MEMREAD=0x33` and `C28X_MEMWRITE=0x34`.

See `contrib/ti-c2000/ccs-native-gti-recovery.md` for the sanitized recovery notes and provenance.
