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
| GigaDevice/WCH/RISC-V MCUs | upstream OpenOCD plus vendor forks when found | GD32VF/GD32E and WCH-Link style configs | Local GigaDevice configs present; WCH-specific review pending |
| WCH community | `https://github.com/jnk0le/openocd-wch` | CH32/WCH-Link support and WinUSB driver notes | Added to audit script as review-only community source |
| Zephyr SDK | `https://github.com/zephyrproject-rtos/openocd` | SDK packaging patches and board-family defaults | Added to audit script as ecosystem source |

## Practical Merge Queue

Start with script/config updates because they are lower risk:

1. Espressif: compare `tcl/target/esp*.cfg`, `tcl/board/esp*.cfg`, and
   `src/jtag/drivers/esp_usb_jtag.c` against `espressif/openocd-esp32`.
2. Raspberry Pi: compare `rp2040.cfg`, `pico-debug.cfg`, and `pico2-debug.cfg`
   against `raspberrypi/openocd`.
3. TI: compare `tcl/interface/ti`, `src/jtag/drivers/xds110.c`, and generated
   TMS320 scripts against `TexasInstruments/ti-openocd`.
4. Microchip: compare `target/microchip`, `programmer/microchip`, and RI4
   files against `microchip-fpga/openocd`.
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
