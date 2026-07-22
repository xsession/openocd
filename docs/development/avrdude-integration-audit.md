# AVRDUDE Integration Audit

This note records how AVRDUDE support is integrated into this OpenOCD fork.
AVRDUDE is not an OpenOCD fork. It is an AVR programming tool and support
catalog, so the first integration step is a command bridge rather than a
wholesale source import.

## Source

| Field | Value |
| --- | --- |
| Repository | `https://github.com/avrdudes/avrdude.git` |
| Local audit copy | `artifacts/vendor-sources/avrdude` |
| Audited commit | `7154723b9efa8bad989b2b339c303aa9d12014e2` |
| Latest checked tag | `v8.2` at `65dd419fdde8a018f718a07351c674121edba2cd` |
| License file | `COPYING` |
| License family | GPL-2.0-or-later notice in the copied license text |
| Primary catalog | `src/avrdude.conf.in` |

## Inventory Snapshot

The July 21, 2026 shallow audit counted:

| Catalog item | Count |
| --- | ---: |
| AVRDUDE `part` blocks | 406 |
| AVRDUDE `programmer` blocks | 174 |
| Programmer blocks derived from parent presets | 59 |

Important implementation files seen in the audit copy include:

- `src/arduino.c`
- `src/avrftdi.c`
- `src/buspirate.c`
- `src/jtag3.c`
- `src/jtagmkI.c`
- `src/jtagmkII.c`
- `src/linuxgpio.c`
- `src/linuxspi.c`
- `src/pickit2.c`
- `src/pickit5.c`
- `src/serialupdi.c`
- `src/serprog.c`
- `src/stk500.c`
- `src/stk500v2.c`
- `src/updi_*.c`
- `src/usbasp.c`
- `src/usbtiny.c`
- `src/wiring.c`

## Integration Decision

| Choice | Decision |
| --- | --- |
| Copy AVRDUDE source into OpenOCD | No |
| Import all part/programmer tables as native data | Yes, generated under `src/avr` |
| Provide immediate broad user access | Yes, through `tcl/programmer/avrdude/common.tcl` |
| Native OpenOCD protocol ports | Deferred to focused backend batches |

The bridge gives OpenOCD users access to all MCU and programmer support present
in their installed AVRDUDE version. That support remains delegated to AVRDUDE;
it is not marked as native OpenOCD debug or flash backend support.

## Added Files

| File | Purpose |
| --- | --- |
| `tcl/programmer/avrdude/common.tcl` | OpenOCD Tcl command bridge to external `avrdude` |
| `docs/programmers/avrdude.md` | User documentation and examples |
| `docs/development/avrdude-integration-audit.md` | Maintainer audit and native-port roadmap |
| `tools/support/generate-avr-catalog.ps1` | Generator for OpenOCD AVR support metadata from `avrdude.conf` |
| `support/catalogs/avrdude/parts.yml` | Generated AVRDUDE part index |
| `support/catalogs/avrdude/programmers.yml` | Generated AVRDUDE programmer index |
| `src/avr/avr_catalog.c` | Native OpenOCD `mcu` and `programmer` command handlers for the compiled catalog |
| `src/avr/avr_catalog.h` | Native catalog API and data structs |
| `src/avr/avr_catalog_data.c` | Generated C data for 406 parts and 174 programmers |
| `src/avr/programmers/usbasp.c` | Native OpenOCD USBasp probe, raw ISP transfer, and signature-read component |
| `src/avr/backends/avrdude/` | Imported AVRDUDE backend source for native OpenOCD protocol-family ports |
| `src/avr/backends/avrdude/SOURCE_MANIFEST.yml` | Imported backend source manifest |
| `support/environments/avr/programming.yml` | Native AVR programming environment metadata and backend queue |

## Generated Support Catalog

The generated catalog brings AVRDUDE's MCU and programmer knowledge into the
OpenOCD support index without claiming native OpenOCD protocol support.

Generate from a specific AVRDUDE catalog:

```powershell
powershell -ExecutionPolicy Bypass -File tools\support\generate-avr-catalog.ps1 -Config path\to\avrdude.conf
```

If no config is passed, the generator checks `AVRDUDE_CONF`, an installed
`avrdude`, and `artifacts/vendor-sources/avrdude/src/avrdude.conf.in`.

The generated support catalog was refreshed from the audited upstream source
copy at `artifacts/vendor-sources/avrdude/src/avrdude.conf.in` and produced:

| Generated item | Count |
| --- | ---: |
| AVRDUDE parts | 406 |
| AVRDUDE programmers | 174 |

The generator also works with older installed AVRDUDE packages, such as the
Arduino-bundled AVRDUDE 6.3-era catalog, but those outputs will naturally
contain fewer parts and programmers.

The same generator writes `src/avr/avr_catalog_data.c`, so the MCU and
programmer catalogs are compiled into the OpenOCD executable. Native query
commands:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "mcu summary" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "mcu list atmega328p" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "programmer list usbasp" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr status" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr backend list" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr backend show usbasp" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr usbasp probe" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr usbasp spi 0xac 0x53 0x00 0x00" -c shutdown
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe -c "avr usbasp signature" -c shutdown
```

The backend source import is intentionally staged before linking the protocol
drivers. The imported library still relies on AVRDUDE-generated parser outputs
and application-level assumptions that need OpenOCD compatibility glue before
each protocol family can be marked integrated.

The native `avr backend` registry is compiled into OpenOCD so each imported
protocol family has an explicit OpenOCD-side status, source-file list, scope,
and next integration step. This registry is the handoff point from source import
to family-by-family native ports.

USBasp now has the first native programmer component in
`src/avr/programmers/usbasp.c`. It uses OpenOCD's libusb helper layer and
AVRDUDE's USBasp vendor request constants to open a device, read firmware
capabilities, enter ISP programming mode, send raw four-byte ISP commands, read
the standard AVR signature bytes, and disconnect. Typed flash, EEPROM, fuse,
and lock-bit operations are still intentionally deferred until memory models
and safety checks are in place.

## Safety Rules

1. Do not vendor a full AVRDUDE checkout into the OpenOCD source tree.
2. Do not claim native OpenOCD support for delegated AVRDUDE operations.
3. Keep fuse and lock-bit operations behind explicit raw commands until a
   safer typed command layer exists.
4. Native C ports must be reviewed by protocol family, not by copying all
   `src/*.c` files at once.
5. Every native backend batch needs Linux/native and Windows package builds
   plus real hardware validation on recoverable parts.

## Native Backend Queue

| Protocol family | Source area | OpenOCD integration type |
| --- | --- | --- |
| ISP and STK500 | `stk500*.c`, `arduino.c`, `wiring.c` | AVR flash/programming backend |
| UPDI | `serialupdi.c`, `updi_*.c` | New UPDI transport/programming backend |
| TPI/PDI | AVRDUDE TPI/PDI paths | New AVR programming backend |
| AVR JTAG/debugWIRE | `jtag*.c` | Debug-capable target/backend work |
| USBasp/USBtiny | `usbasp.c`, `usbtiny.c` | USBasp ISP command/signature native; USBtiny staged |
| FTDI bitbang/JTAG | `avrftdi*.c` | Adapter/protocol bridge |
| Linux GPIO/SPI | `linuxgpio.c`, `linuxspi.c` | Host-specific programmer backend |
| Serial bootloaders | `arduino.c`, `urclock.c`, `xbee.c` | External or native bootloader backend |
| PICkit AVR modes | `pickit*.c` | Compare with local Microchip bridge before porting |

## Validation

Syntax and command-building checks:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f programmer/avrdude/common.tcl `
  -c "avrdude help" `
  -c shutdown

.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f programmer/avrdude/common.tcl `
  -c "avrdude dry_run on" `
  -c "avrdude programmer arduino" `
  -c "avrdude part atmega328p" `
  -c "avrdude port COM1" `
  -c "avrdude baud 115200" `
  -c "avrdude command program docs/index.md" `
  -c shutdown
```

Real hardware programming remains dependent on a locally installed AVRDUDE
binary, the selected programmer, and a recoverable AVR target.
