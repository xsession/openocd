# CCS-derived C28x data used by this OpenOCD backend

This file records the CCS metadata that was extracted from the uploaded
`ccs_base.zip` package and folded into the OpenOCD C28x target backend.

## XML sources

- `ccs_base/common/targetdb/cpus/c28xx.xml`
- `ccs_base/common/targetdb/drivers/TI_reg_ids/TMS320C28XX_regids.xml`
- `ccs_base/common/targetdb/drivers/tixds100c28x.xml`
- `ccs_base/common/targetdb/drivers/tixds100v2c28x.xml`
- `ccs_base/common/targetdb/drivers/tixds510c28x.xml`
- `ccs_base/common/targetdb/drivers/tixds560c28x.xml`
- `ccs_base/common/targetdb/devices/f28069.xml`
- `ccs_base/common/targetdb/devices/f280049.xml`
- `ccs_base/common/targetdb/devices/f28m35h52c1.xml`
- `ccs_base/common/targetdb/devices/f28m35m52c1.xml`

## Core register IDs

| Register | TI register ID | Width |
| --- | ---: | ---: |
| PC / IC | 0 | 24 |
| SP / FP | 1 | 16 |
| ACC | 2 | 32 |
| P | 3 | 32 |
| XT | 4 | 32 |
| ST0 | 5 | 16 |
| ST1 | 6 | 16 |
| XAR0 | 7 | 32 |
| XAR1 | 8 | 32 |
| XAR2 | 9 | 32 |
| XAR3 | 10 | 32 |
| XAR4 | 11 | 32 |
| XAR5 | 12 | 32 |
| XAR6 | 13 | 32 |
| XAR7 | 14 | 32 |
| IER | 15 | 16 |
| IFR | 16 | 16 |
| DP | 17 | 16 |
| DBGIER | 18 | 16 |
| RPC | 19 | 24 |
| RPTC | 20 | 16 |

The OpenOCD register cache now stores both the OpenOCD cache index and the TI
register ID.  Register read/write packets use the TI ID, not the cache index.

## Device routing metadata

| Device XML | CCS part/device | C28x path | Port | GEL |
| --- | --- | --- | ---: | --- |
| `f28069.xml` | `TMS320F28069` | direct C28xx CPU instance | unset | `../../emulation/gel/f28069.gel` |
| `f280049.xml` | `TMS320F280049` | `IcePick_C_0/Subpath_0/C28xx_CPU1` | `0x10` | `../../emulation/gel/f280049.gel` |
| `f28m35h52c1.xml` | `F28M35H52C1` | `IcePick_C_0/C28x/C28xx_0` | `0x11` | `../../emulation/gel/f28m35h52c1_c28.gel` |
| `f28m35m52c1.xml` | `F28M35M52C1` | `IcePick_C_0/C28x/C28xx_0` | `0x11` | `../../emulation/gel/f28m35m52c1_c28.gel` |

For F28M35x, the Cortex-M3 side is on ICEPick port `0x10`; the C28x side is
on port `0x11`.

## XDS driver data

The C28x driver XMLs point to `tixds28x.dvr` or `tixds560c28x.dvr` and use
`ProcID=0x5000A3F8`.

Binary inspection found these C28x-specific XDS110 firmware command IDs in
`ccs_base/common/uscif/jscxds110.dll`:

| Symbol/string | Command byte |
| --- | ---: |
| `C28X_MEMREAD` | `0x33` |
| `C28X_MEMWRITE` | `0x34` |

The existing OpenOCD XDS110 driver already reserves command IDs through
`0x3c`; these C28x commands sit immediately after `XDS_SET_SUPPLY=0x32`.
The exact host packet has address and mode fields plus data payload, but only
the memory command IDs are safe to store without additional hardware testing.

## Still not guessed

`tixds28x.dvr` exposes high-level `GTI_HALT`, `GTI_RUN`, `GTI_STEP`,
`GTI_READREG`, and `GTI_WRITEREG` entry points, but the disassembly routes
these through TI-private PRSC/SMG/XDSFast layers.  This patch therefore does
not invent private C28x core halt/register packets.  The backend remains
fail-closed until those packets are recovered from a deeper reverse-engineering
pass or a hardware trace.
