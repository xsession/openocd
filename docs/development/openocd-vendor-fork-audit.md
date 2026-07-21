# OpenOCD Vendor Fork Audit

This document tracks external OpenOCD forks, Arduino ecosystems, MCU vendors,
and programmer/debugger support that should be considered when expanding this
fork. It is a maintainer checklist, not a blanket instruction to copy whole
repositories.

## Import Rules

Use this order when integrating support:

1. Prefer upstream OpenOCD files already present in this tree.
2. Import Tcl board, target, and interface configs only when they are small,
   GPL-compatible, and still relevant to current boards.
3. Import C drivers only after a source diff against upstream OpenOCD and a
   build test on Linux and Windows cross builds.
4. Keep generated MCU catalogs under a vendor-specific generated folder.
5. Record the source repository, branch/tag, license, and local validation
   command for each imported family.

Do not vendor a full OpenOCD fork over this tree. Forks often carry old
submodule pins, old build glue, and local workarounds that conflict with newer
OpenOCD internals.

## Current Local Coverage

The local tree already has broad MCU and adapter coverage:

- Adapter drivers: CMSIS-DAP, ESP USB-JTAG, J-Link, KitProg, Nu-Link, ST-Link,
  TI ICDI, TI XDS110, FTDI-based XDS100v1/v2/v3 configs, libjaylink.
- Vendor target/config folders: `ti`, `microchip`, `nordic`, `nxp`, `st`,
  `silabs`, `infineon`, `gigadevice`, `hpmicro`, `geehy`, `artery`.
- Notable local custom work: TI C2000/C28x discovery, generated TI TMS320
  configs, Microchip RI4/PICkit/ICD support, Docker Windows package with
  libwdi/Zadig driver helper.

## External Sources To Track

| Ecosystem | Source | What to compare | Local status |
| --- | --- | --- | --- |
| OpenOCD upstream | `https://github.com/openocd-org/openocd` | Baseline targets, flash drivers, adapter drivers, Tcl scripts, command behavior | Baseline plus local extensions |
| Arduino OpenOCD | `https://github.com/arduino/OpenOCD` | Arduino-packaged OpenOCD scripts and board defaults | Track for package conventions |
| Arduino Mbed core | `https://github.com/arduino/ArduinoCore-mbed` | CMSIS-DAP/J-Link/OpenOCD use for Arduino Mbed boards | Track board/package naming |
| STM32duino | `https://github.com/stm32duino/Arduino_Core_STM32` | STM32 board catalog and upload/debug assumptions | Local STM32 support already broad |
| Espressif | `https://github.com/espressif/openocd-esp32` | ESP32-C/P/S/H target files, ESP USB-JTAG, flash/program helpers | Local ESP target and adapter code present; compare newer ESP32-P4/C5/C61 work |
| Raspberry Pi | `https://github.com/raspberrypi/openocd` | RP2040/RP2350 scripts, Pico debug boards, SWD probe assumptions | Local `rp2040.cfg`, `pico-debug.cfg`, `pico2-debug.cfg` present |
| RISC-V collaboration | `https://github.com/riscv-collab/riscv-openocd` | RISC-V debug module fixes, SBA behavior, target quirks | Local RISC-V target present; code diff required |
| Texas Instruments | `https://github.com/TexasInstruments/ti-openocd` | TI release branch, XDS110/XDS100 configs, AM/K3/MSP/C2000 target scripts | Local TI tree heavily extended; use as primary TI diff source |
| Microchip FPGA | `https://github.com/microchip-fpga/openocd` | PIC64GX/MPFS board and target scripts, FlashPro interfaces | Local Microchip target/programmer work present; compare for PIC64GX naming |
| Nuvoton | `https://github.com/OpenNuvoton/Nuvoton_Tools` | Nu-Link/Nu-Link2/Nu-Link3 tooling, customized OpenOCD references | Local Nu-Link driver present; driver/package diff required |
| Nuvoton OpenOCD | `https://github.com/OpenNuvoton/OpenOCD-Nuvoton` | NuMicro M0/M4/M23 targets and legacy Nu-Link flow | Added to audit script |
| Nordic | `https://github.com/NordicSemiconductor` and upstream OpenOCD | nRF51/nRF52/nRF53/nRF54/nRF91 configs and flash behavior | Local Nordic target/board configs present |
| NXP | `https://github.com/nxp-mcuxpresso` and upstream OpenOCD | MCUXpresso debug defaults, LinkServer/OpenOCD board naming | Local Kinetis/LPC/i.MX/NXP configs present |
| Silicon Labs | `https://github.com/SiliconLabs` and upstream OpenOCD | EFM32/EFR32/XG series scripts, kit naming | Local Silicon Labs Series 0/1/2 and XG configs present |
| Infineon/Cypress | upstream OpenOCD and Infineon examples | XMC and PSoC targets, KitProg behavior | Local XMC and PSoC flash/target support present |
| GigaDevice/WCH/RISC-V MCUs | upstream OpenOCD plus vendor forks when found | GD32VF/GD32E and WCH-Link style configs | Local GigaDevice configs are current; WCH backend deferred |
| WCH community | `https://github.com/jnk0le/openocd-wch` | CH32/WCH-Link support and WinUSB driver notes | Added to audit script as review-only community source |
| Zephyr SDK | `https://github.com/zephyrproject-rtos/openocd` | SDK packaging patches and board-family defaults | Added to audit script as ecosystem source |

## Practical Merge Queue

Start with script/config updates because they are lower risk:

1. TI: compare `tcl/interface/ti`, `src/jtag/drivers/xds110.c`, and generated
   TMS320 scripts against `TexasInstruments/ti-openocd`.
2. Espressif: compare `tcl/target/esp*.cfg`, `tcl/board/esp*.cfg`, and
   `src/jtag/drivers/esp_usb_jtag.c` against `espressif/openocd-esp32`.
   This is a backend integration, not a Tcl-only import.
3. Microchip: compare `target/microchip`, `programmer/microchip`, and RI4
   files against `microchip-fpga/openocd`.
4. WCH: import CH32 only as a complete WCH-Link/WCH-RISC-V backend batch.
5. RISC-V: compare only `src/target/riscv` after the MCU-specific config work,
   because this is a higher-risk core target backend.

## Validation Commands

Use syntax checks before hardware tests:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/ti/launchxl-f28069m-xds100v2.cfg -c init -c shutdown
```

For config-only imports, add at least one dry-run command per board family.
For C driver imports, rebuild the Docker Windows package and a native Linux
build before marking support as integrated.

## Current Decision

This fork should become a curated OpenOCD superset, not an unstructured fork
dump. The next concrete work item is a per-source diff tool that checks external
forks into `artifacts/vendor-audit/` and emits:

- new Tcl scripts not present locally,
- modified Tcl scripts,
- modified C backends/drivers,
- configure/build option differences,
- license files and copyright deltas.

Run the audit with:

```powershell
.\tools\vendor\openocd-vendor-audit.ps1 -Fetch
```

The script writes `artifacts/vendor-audit/openocd-vendor-file-delta.csv`. Review
that CSV one ecosystem at a time, then import small Tcl/config changes first and
C source changes only after a focused code review.

## Audit Snapshot: 2026-07-21

The first expanded GitHub audit cloned 10 source ecosystems and wrote 8,259
candidate file deltas:

| Ecosystem | Changed local-path matches | New upstream paths |
| --- | ---: | ---: |
| OpenOCD upstream | 22 | 8 |
| Arduino OpenOCD | 824 | 124 |
| Espressif | 1,577 | 112 |
| Raspberry Pi | 553 | 138 |
| RISC-V collaboration | 420 | 131 |
| Texas Instruments | 551 | 154 |
| Microchip FPGA | 541 | 121 |
| Nuvoton legacy OpenOCD | 818 | 185 |
| WCH community | 1,122 | 148 |
| Zephyr SDK | 561 | 149 |

This is not a merge count. It is the triage queue for deciding what is worth
bringing in. Start with new Tcl board/target/interface scripts, then review C
drivers and target backends one family at a time.

## Integrated Batch 1: 2026-07-21

Imported from OpenOCD upstream:

- `tcl/target/microchip/sama7d6.cfg`
- `tcl/target/microchip/sama7g5.cfg`
- `tcl/board/microchip/sama7d65-curiosity.cfg`
- `tcl/board/microchip/sama7g54-ek.cfg`
- `tcl/target/stm32wba2x.cfg`
- `tcl/board/st/nucleo-u575zi-q.cfg`

Imported from Texas Instruments `ti-openocd` and normalized to this repo's
`tcl/*/ti/` layout:

- `src/flash/nor/mspm33.c`
- `tcl/target/ti/mspm33.cfg`
- `tcl/board/ti/mspm33-launchpad.cfg`
- `tcl/target/ti/cc35x1e.cfg`
- `tcl/board/ti/cc35x1e-launchpad.cfg`

The MSPM33 flash driver is registered in `src/flash/nor/Makefile.am`,
`src/flash/nor/driver.h`, and `src/flash/nor/drivers.c`.

Validation:

```powershell
docker buildx build --progress=plain -f docker/Dockerfile.windows-cross --target export --output type=local,dest=artifacts/windows .
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f interface/jlink.cfg -c "transport select swd" -f board/microchip/sama7d65-curiosity.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/microchip/sama7g54-ek.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/st/nucleo-u575zi-q.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/ti/mspm33-launchpad.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/ti/cc35x1e-launchpad.cfg -c shutdown
```

## Integrated Batch 2: 2026-07-21

Imported from Texas Instruments `ti-openocd` and normalized to this repo's
`src/flash/nor/` and `tcl/*/ti/` layout:

- `src/flash/nor/cc23xx.c`
- `src/flash/nor/cc23xx.h`
- `src/flash/nor/cc27xx.c`
- `src/flash/nor/cc27xx.h`
- `src/flash/nor/cc_lpf3_base.c`
- `src/flash/nor/cc_lpf3_base.h`
- `src/flash/nor/cc_lpf3_flash.c`
- `src/flash/nor/cc_lpf3_flash.h`
- `tcl/target/ti/lpf3.cfg`
- `tcl/target/ti/cc23xx.cfg`
- `tcl/target/ti/cc27xx.cfg`
- `tcl/target/ti/cc2341.cfg`
- `tcl/board/ti/lp-em-cc2340r5.cfg`
- `tcl/board/ti/lp-em-cc2340r53.cfg`
- `tcl/board/ti/lp-em-cc2341.cfg`
- `tcl/board/ti/lp-em-cc2745p10.cfg`
- `tcl/board/ti/lp-em-cc2745r10.cfg`
- `tcl/board/ti/lp-em-cc2745r74.cfg`
- `tcl/board/ti/lp-em-cc2755p10.cfg`
- `tcl/board/ti/lp-em-cc2755p20.cfg`
- `tcl/board/ti/lp-em-cc2755r10.cfg`
- `tcl/board/ti/lp-em-cc2755r74.cfg`
- `tcl/board/ti/lp-em-cc2765r10.cfg`

The CC23xx/CC27xx flash drivers are registered in
`src/flash/nor/Makefile.am`, `src/flash/nor/driver.h`, and
`src/flash/nor/drivers.c`.

The imported LPF3 target scripts use `dap create -switch-thru-dormant`.
This fork already carried the lower-level dormant-mode transport state, so
`src/target/arm_dap.c` now accepts that DAP creation option and maps it to
`dap->dap.switch_through_dormant`.

Validation:

```powershell
docker buildx build --progress=plain -f docker/Dockerfile.windows-cross --target export --output type=local,dest=artifacts/windows .

$OpenOcd = Resolve-Path artifacts\windows\openocd-windows-x86_64\bin\openocd.exe
$Scripts = Resolve-Path artifacts\windows\openocd-windows-x86_64\share\openocd\scripts
$Boards = Get-ChildItem artifacts\windows\openocd-windows-x86_64\share\openocd\scripts\board\ti\lp-em-cc*.cfg | Sort-Object Name
$Failed = @()
foreach ($Board in $Boards) {
    & $OpenOcd -s $Scripts -f ("board/ti/" + $Board.Name) -c shutdown
    if ($LASTEXITCODE -ne 0) { $Failed += $Board.Name }
}
if ($Failed.Count) { throw "Failed boards: $($Failed -join ', ')" }
```

Result: all 11 LPF3 board configs loaded with the rebuilt Windows package.

## Integrated Batch 3: 2026-07-21

Imported from Texas Instruments `ti-openocd` and normalized to this repo's
`src/flash/nor/`, `contrib/loaders/flash/`, and `tcl/*/ti/` layout:

- `src/flash/nor/am13e230x.c`
- `src/flash/nor/am13e230x.h`
- `contrib/loaders/flash/am13e230x/`
- `tcl/target/ti/am13e230x.cfg`
- `tcl/board/ti/am13e230x-launchpad.cfg`

The AM13E230x flash driver is registered as `am13` in
`src/flash/nor/Makefile.am`, `src/flash/nor/driver.h`, and
`src/flash/nor/drivers.c`.

The imported board file was adjusted to this tree's board style: it defines the
XDS110 adapter and target, but does not automatically run `init` or
`reset halt`. Use explicit commands when an immediate attach is desired:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\tcl -f board/ti/am13e230x-launchpad.cfg -c "init; reset halt"
```

Updated from OpenOCD upstream:

- `tcl/target/stm32wba5x.cfg`
- `tcl/target/stm32wba6x.cfg`

Both ST WBA files now use the upstream RCC_CFGR1 mask for selecting HSI16 in
`reset-init`.

Validation:

```powershell
docker buildx build --progress=plain -f docker/Dockerfile.windows-cross --target export --output type=local,dest=artifacts/windows .
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts -f interface/dummy.cfg -f target/ti/am13e230x.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts -f interface/dummy.cfg -f target/stm32wba5x.cfg -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -s .\artifacts\windows\openocd-windows-x86_64\share\openocd\scripts -f interface/dummy.cfg -f target/stm32wba6x.cfg -c shutdown
```

Deferred after review:

- WCH community `wch-riscv.cfg` depends on custom `wlinke`, `sdi`,
  `wch_riscv`, and WCH flash backends. Do not import only the Tcl.
- Espressif ESP32-C5, ESP32-C61, and ESP32-P4 scripts depend on new
  Espressif target types such as `esp32c5`, `esp32c61`, and `esp32p4`.
  Treat these as a C backend integration batch.
- Nuvoton legacy M23/M23_NS scripts depend on newer `numicro.c` flash-region
  handling. Import the flash-driver update before adding those target aliases.

## Remaining Vendor Sweep: 2026-07-21

This pass checked the rest of the audited vendor and ecosystem forks for safe
config-only imports. No additional source files were imported in this sweep:
the useful standalone support is already present locally, and the remaining
deltas require paired C backend work.

Covered locally:

| Ecosystem | Decision |
| --- | --- |
| Microchip FPGA | Local `tcl/interface/microchip`, `tcl/programmer/microchip`, and `tcl/target/microchip` coverage already includes MPFS/PIC64GX/SAMA7 families and local RI4 work. No clean Microchip-only import was found in the audited checkout. |
| Silicon Labs | Local `tcl/target/silabs` already includes Series 0/1/2 and XG21/XG23/XG24/XG25/XG26/XG28/XG29 configs, with matching kit boards. |
| ST | Local STM32 coverage is ahead of the audited forks for U0/U3/MP2 families; WBA5/WBA6 mask updates were already imported in Batch 3. |
| Nordic | Local `tcl/target/nordic` and `tcl/board/nordic` already cover nRF51/nRF52/nRF53/nRF54L/nRF91 families. |
| NXP | Local Kinetis, LPC, i.MX, and NXP board/target coverage is already broad. No self-contained MCUXpresso config import was identified. |
| Raspberry Pi | Local scripts already include RP2040/RP2350 and Pico/Pico 2 debug board flows. The audited Raspberry Pi fork does not add a cleaner standalone import. |
| GigaDevice | `gd32e23x.cfg` matches the WCH community copy. Local `gd32vf103.cfg` is newer and more robust, with SPDX metadata, parameterized work area, watchdog handling, and reset-state handling. |
| TI native SWD | The audited `ti_am625_swd_native.cfg` and `ti_j721e_swd_native.cfg` are covered by local `tcl/board/ti/am625-self-hosted.cfg` and `tcl/board/ti/j721e-self-hosted.cfg`. |

Deferred backend batches:

| Ecosystem | Why not Tcl-only |
| --- | --- |
| Espressif | ESP32-C5/C61/P4/H21/H4/S31 scripts depend on Espressif-specific target types and flash helpers. Import as a full `src/target/espressif` and flash-driver update with build and dummy-config tests. |
| WCH | CH32 support depends on WCH adapter/transport/target/flash code (`wlinke`, `sdi`, `wch_riscv`, `wcharm`, `wchriscv`). Config-only import would create broken targets. |
| Nuvoton legacy | M23/M23_NS configs depend on a newer `numicro.c` implementation with flash-region handling. Import the flash backend first, then add target aliases. |
| Zephyr SDK | `rv32m1` and `nds32` families depend on target backend code that is not present in this tree. Treat as a backend integration, not board-file cleanup. |
| Arduino OpenOCD | The useful deltas are mostly old NDS32/package flow files. Import only after deciding whether NDS32 should be restored as a supported target backend. |
| RISC-V collaboration | Contains core RISC-V backend behavior changes. Review after MCU-specific imports, with hardware or simulator validation, because regressions would affect many targets. |

Next integration candidates:

1. Complete the TI hardware path first: XDS100v2/XDS110 driver packaging,
   LaunchXL-F28069M attach flow, and C28x target creation tests.
2. Import Espressif as a full backend batch if ESP32-C5/C61/P4 support is
   needed.
3. Import WCH as a full backend batch if CH32/WCH-Link support is needed.
