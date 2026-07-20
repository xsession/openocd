# TI TMS320 family support generated from CCS targetdb

This repository imports TI Code Composer Studio `ccs_base` target metadata to broaden OpenOCD coverage across TMS320 DSP families.

## Implemented layers

- `c28x` remains the real C28x/C2000 OpenOCD target backend with CCS-derived register IDs and recovered GTI/TRG operation metadata.
- `tms320` is a generic metadata/debug-model backend for non-C28x TMS320 DSP families: C55x, C62x/C64x/C64x+/C646x/C66x/C674x, C71x and C75x.
- Generated target configs live under `tcl/target/ti/tms320/generated/`.
- Register-ID tables are generated from `common/targetdb/drivers/TI_reg_ids/*.xml`.
- Device/core/GEL/ICEPick metadata is generated from `common/targetdb/devices/*.xml`.

## Safety boundary

The non-C28x `tms320` backend intentionally fails closed for halt/resume/step/memory operations. CCS exposes these through TI-private native drivers (`tixds55x.dvr`, `tixds6400_plus.dvr`, `tixds510c71x.dvr`, etc.); the public XML gives exact register IDs and ProcIDs but not a complete public JTAG packet protocol.

## Family register coverage

| Family | ISA | ProcID | CCS driver | Register IDs |
|---|---:|---:|---|---:|
| `c55xx` | `TMS320C55XX` | `0x50015400` | `tixds55x.dvr` | 292 |
| `c64xx` | `TMS320C64XX` | `0x500193F8` | `tixds6400_11.dvr` | 921 |
| `c64xp` | `TMS320C64XP` | `0x50019348` | `tixds6400_plus.dvr` | 921 |
| `c646x` | `TMS320C646X` | `0x50019350` | `tixds6400_plus.dvr` | 921 |
| `c66xx` | `TMS320C66XX` | `0x50019BF8` | `tixds6400_plus.dvr` | 921 |
| `c674x` | `TMS320C674X` | `0x50019F40` | `tixds6400_plus.dvr` | 921 |
| `c6xxx` | `TMS320C6XXX` | `0x50018B20` | `tixds6000.dvr` | 885 |
| `c620x` | `TMS320C620X` | `0x50018B20` | `tixds6000.dvr` | 885 |
| `c621x` | `TMS320C621X` | `0x50018B28` | `tixds6000.dvr` | 885 |
| `c670x` | `TMS320C670X` | `0x50019F20` | `tixds6000.dvr` | 885 |
| `c671x` | `TMS320C671X` | `0x50019F28` | `tixds6000.dvr` | 885 |
| `c672x` | `TMS320C672X` | `0x50019F30` | `tixds6000.dvr` | 885 |
| `c71x` | `TMS320C71XX` | `0x5001C7F8` | `tixds510c71x.dvr` | 486 |
| `c71x_v2` | `TMS320C71XX` | `0x5001C7F8` | `tixds510c71x.dvr` | 486 |
| `c75x` | `TMS320C75XX` | `0x5001D7F8` | `tixds510c71x.dvr` | 439 |

## Generated device configs

Generated 183 device configuration files.

- `66AK2E05`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/66ak2e05.cfg`
- `66AK2G01`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/66ak2g01.cfg`
- `66AK2G02`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/66ak2g02.cfg`
- `66AK2G12`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/66ak2g12.cfg`
- `66AK2H06`: `c66xx`, 4 CPU target(s), `target/ti/tms320/generated/66ak2h06.cfg`
- `66AK2H12`: `c66xx`, 8 CPU target(s), `target/ti/tms320/generated/66ak2h12.cfg`
- `66AK2H14`: `c66xx`, 8 CPU target(s), `target/ti/tms320/generated/66ak2h14.cfg`
- `66AK2L06`: `c66xx`, 4 CPU target(s), `target/ti/tms320/generated/66ak2l06.cfg`
- `AM273x`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/am273x.cfg`
- `AM5706`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/am5706.cfg`
- `AM5708`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/am5708.cfg`
- `AM5716`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/am5716.cfg`
- `AM5718`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/am5718.cfg`
- `AM5726`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5726.cfg`
- `AM5726_RevA`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5726_reva.cfg`
- `AM5728`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5728.cfg`
- `AM5728_RevA`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5728_reva.cfg`
- `AM5729`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5729.cfg`
- `AM5746`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5746.cfg`
- `AM5748`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5748.cfg`
- `AM5749`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5749.cfg`
- `AM5766`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5766.cfg`
- `AM5768`: `c66xx`, 2 CPU target(s), `target/ti/tms320/generated/am5768.cfg`
- `AWR1642`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/awr1642.cfg`
- `AWR1843`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/awr1843.cfg`
- `AWR2943`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/awr2943.cfg`
- `AWR2944`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/awr2944.cfg`
- `AWR6843`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/awr6843.cfg`
- `AWR6843AOP`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/awr6843aop.cfg`
- `F28M35E20B1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35e20b1.cfg`
- `F28M35H22C1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35h22c1.cfg`
- `F28M35H52C1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35h52c1.cfg`
- `F28M35M20B1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35m20b1.cfg`
- `F28M35M22C1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35m22c1.cfg`
- `F28M35M52C1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m35m52c1.cfg`
- `F28M36H33B2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36h33b2.cfg`
- `F28M36H33C2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36h33c2.cfg`
- `F28M36H53B2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36h53b2.cfg`
- `F28M36H53C2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36h53c2.cfg`
- `F28M36P53C2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36p53c2.cfg`
- `F28M36P63C2`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/f28m36p63c2.cfg`
- `IWR1642`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/iwr1642.cfg`
- `IWR1843`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/iwr1843.cfg`
- `IWR1843AOP`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/iwr1843aop.cfg`
- `IWR6843`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/iwr6843.cfg`
- `IWR6843AOP`: `c674x`, 1 CPU target(s), `target/ti/tms320/generated/iwr6843aop.cfg`
- `TCI6630K2L`: `c66xx`, 4 CPU target(s), `target/ti/tms320/generated/tci6630k2l.cfg`
- `TCI6634K2K`: `c66xx`, 8 CPU target(s), `target/ti/tms320/generated/tci6634k2k.cfg`
- `TCI6636K2H`: `c66xx`, 8 CPU target(s), `target/ti/tms320/generated/tci6636k2h.cfg`
- `TCI6638K2K`: `c66xx`, 8 CPU target(s), `target/ti/tms320/generated/tci6638k2k.cfg`
- `TMS320C2801`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c2801.cfg`
- `TMS320C2802`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c2802.cfg`
- `TMS320C2810`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c2810.cfg`
- `TMS320C2811`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c2811.cfg`
- `TMS320C2812`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c2812.cfg`
- `TMS320C28341`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28341.cfg`
- `TMS320C28342`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28342.cfg`
- `TMS320C28343`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28343.cfg`
- `TMS320C28344`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28344.cfg`
- `TMS320C28345`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28345.cfg`
- `TMS320C28346`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320c28346.cfg`
- `TMS320F2800132`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800132.cfg`
- `TMS320F2800133`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800133.cfg`
- `TMS320F2800135`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800135.cfg`
- `TMS320F2800137`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800137.cfg`
- `TMS320F2800153`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800153.cfg`
- `TMS320F2800155`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800155.cfg`
- `TMS320F2800155-Q1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800155_q1.cfg`
- `TMS320F2800157`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800157.cfg`
- `TMS320F2800157-Q1`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2800157_q1.cfg`
- `TMS320F280021`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280021.cfg`
- `TMS320F280022`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280022.cfg`
- `TMS320F280023`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280023.cfg`
- `TMS320F280023C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280023c.cfg`
- `TMS320F280024`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280024.cfg`
- `TMS320F280024C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280024c.cfg`
- `TMS320F280025`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280025.cfg`
- `TMS320F280025C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280025c.cfg`
- `TMS320F280033`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280033.cfg`
- `TMS320F280034`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280034.cfg`
- `TMS320F280036`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280036.cfg`
- `TMS320F280036C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280036c.cfg`
- `TMS320F280037`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280037.cfg`
- `TMS320F280037C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280037c.cfg`
- `TMS320F280038`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280038.cfg`
- `TMS320F280038C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280038c.cfg`
- `TMS320F280039`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280039.cfg`
- `TMS320F280039C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280039c.cfg`
- `TMS320F280040`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280040.cfg`
- `TMS320F280040C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280040c.cfg`
- `TMS320F280041`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280041.cfg`
- `TMS320F280041C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280041c.cfg`
- `TMS320F280045`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280045.cfg`
- `TMS320F280048`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280048.cfg`
- `TMS320F280048C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280048c.cfg`
- `TMS320F280049`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280049.cfg`
- `TMS320F280049C`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280049c.cfg`
- `TMS320F280049M`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280049m.cfg`
- `TMS320F2801`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2801.cfg`
- `TMS320F28015`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28015.cfg`
- `TMS320F28016`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28016.cfg`
- `TMS320F2802`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2802.cfg`
- `TMS320F28020`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28020.cfg`
- `TMS320F280200`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280200.cfg`
- `TMS320F28021`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28021.cfg`
- `TMS320F28022`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28022.cfg`
- `TMS320F280220`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280220.cfg`
- `TMS320F28023`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28023.cfg`
- `TMS320F280230`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280230.cfg`
- `TMS320F28026`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28026.cfg`
- `TMS320F280260`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280260.cfg`
- `TMS320F28027`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28027.cfg`
- `TMS320F280270`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f280270.cfg`
- `TMS320F28030`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28030.cfg`
- `TMS320F28031`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28031.cfg`
- `TMS320F28032`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28032.cfg`
- `TMS320F28033`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28033.cfg`
- `TMS320F28034`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28034.cfg`
- `TMS320F28035`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28035.cfg`
- `TMS320F28044`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28044.cfg`
- `TMS320F28050`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28050.cfg`
- `TMS320F28051`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28051.cfg`
- `TMS320F28052`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28052.cfg`
- `TMS320F28052F`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28052f.cfg`
- `TMS320F28052M`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28052m.cfg`
- `TMS320F28053`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28053.cfg`
- `TMS320F28054`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28054.cfg`
- `TMS320F28054F`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28054f.cfg`
- `TMS320F28054M`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28054m.cfg`
- `TMS320F28055`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28055.cfg`
- `TMS320F2806`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2806.cfg`
- `TMS320F28062`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28062.cfg`
- `TMS320F28063`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28063.cfg`
- `TMS320F28064`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28064.cfg`
- `TMS320F28065`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28065.cfg`
- `TMS320F28066`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28066.cfg`
- `TMS320F28067`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28067.cfg`
- `TMS320F28068`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28068.cfg`
- `TMS320F28069`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28069.cfg`
- `TMS320F28074`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28074.cfg`
- `TMS320F28075`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28075.cfg`
- `TMS320F28076`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28076.cfg`
- `TMS320F28079`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28079.cfg`
- `TMS320F2808`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2808.cfg`
- `TMS320F2809`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2809.cfg`
- `TMS320F2810`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2810.cfg`
- `TMS320F2811`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2811.cfg`
- `TMS320F2812`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f2812.cfg`
- `TMS320F28232`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28232.cfg`
- `TMS320F28234`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28234.cfg`
- `TMS320F28235`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28235.cfg`
- `TMS320F28332`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28332.cfg`
- `TMS320F28333`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28333.cfg`
- `TMS320F28334`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28334.cfg`
- `TMS320F28335`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28335.cfg`
- `TMS320F28374D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28374d.cfg`
- `TMS320F28374S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28374s.cfg`
- `TMS320F28375D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28375d.cfg`
- `TMS320F28375S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28375s.cfg`
- `TMS320F28376D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28376d.cfg`
- `TMS320F28376S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28376s.cfg`
- `TMS320F28377D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28377d.cfg`
- `TMS320F28377S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28377s.cfg`
- `TMS320F28378D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28378d.cfg`
- `TMS320F28378S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28378s.cfg`
- `TMS320F28379D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28379d.cfg`
- `TMS320F28379S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28379s.cfg`
- `TMS320F2837HD`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f2837hd.cfg`
- `TMS320F28384D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28384d.cfg`
- `TMS320F28384S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28384s.cfg`
- `TMS320F28386D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28386d.cfg`
- `TMS320F28386S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28386s.cfg`
- `TMS320F28388D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28388d.cfg`
- `TMS320F28388S`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28388s.cfg`
- `TMS320F28PLC83`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28plc83.cfg`
- `TMS320F28PLC84`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28plc84.cfg`
- `TMS320F28PLC85`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28plc85.cfg`
- `TMS320F28PLC90D`: `c28x`, 2 CPU target(s), `target/ti/tms320/generated/tms320f28plc90d.cfg`
- `TMS320F28PLC93`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28plc93.cfg`
- `TMS320F28PLC95`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320f28plc95.cfg`
- `TMS320R2810`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320r2810.cfg`
- `TMS320R2812`: `c28x`, 1 CPU target(s), `target/ti/tms320/generated/tms320r2812.cfg`
- `TPR12`: `c66xx`, 1 CPU target(s), `target/ti/tms320/generated/tpr12.cfg`

## Generic family templates

In addition to the CCS device-generated files, this patch adds generic family templates under `tcl/target/ti/tms320/family/` for TMS320 cores that are present in the CCS CPU/driver/register database but do not have a board/device XML entry in the supplied CCS package. These templates cover C55xx, C62xx/C64xx/C66xx/C67xx/C674x, C71x, and C75x families and expose CCS-derived register IDs and ProcID metadata through the `tms320` command group.
