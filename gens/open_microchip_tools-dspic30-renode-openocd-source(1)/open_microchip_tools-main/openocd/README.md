# OpenOCD integration

`overlay/` is the maintained OpenOCD integration. The old patch under
`patches/` is retained only for history and must not be used for production.

## Install into an OpenOCD checkout

```bash
python openocd/install_overlay.py /path/to/openocd
cd /path/to/openocd
./bootstrap
./configure --enable-dummy
make -j
```

The dummy adapter is intentional. The target uses a synthetic TAP only to
satisfy OpenOCD's target model; USB and Renode traffic go through the JSON
bridge, and the Tcl interface suppresses physical JTAG scans.

The installer is idempotent and performs both target and NOR-flash
registration:

1. copies the bridge target, flash driver, and Tcl configuration files;
2. adds the target and flash sources to their Automake source lists;
3. declares and registers `mchp_ri4_bridge_target` and `mchp_ri4_flash` in
   OpenOCD's target/flash driver tables.

The target communicates with `mchp-openocd-bridge` over newline-delimited JSON.
It does not access the PICkit USB device directly, so only the bridge process
must own the PK4/ICD4 USB interface.

## Implemented target operations

The maintained overlay maps OpenOCD operations to bridge commands:

- examine, status polling, halt, resume, single-step, and reset;
- PC register read/write;
- program-memory read/write;
- hardware breakpoints and data watchpoints when the backend exposes them;
- standard OpenOCD NOR commands through the `mchp_ri4` flash bank;
- compatibility commands `mchp_ri4 erase`, `program`, `verify`, and
  `capabilities`.

Support is capability-driven. A device family that lacks a required RI4 script
is reported as unsupported rather than simulated locally.

## Standard flash-bank configuration

Renode profiles set the flash geometry automatically. Hardware configurations
must provide the device geometry before sourcing `target/mchp-ri4.cfg`:

```tcl
set MCHP_RI4_FLASH_BASE 0
set MCHP_RI4_FLASH_SIZE 0x20000
set MCHP_RI4_ERASE_MODE 0
```

The driver models one erase sector covering the configured bank because the
current bridge API exposes chip erase rather than portable per-sector geometry.
Writes and verification still operate on arbitrary image ranges.

Representative commands:

```text
init
halt
flash info 0
flash erase_sector 0 0 last
flash write_image firmware.hex
verify_image firmware.hex
reset halt
```

`flash write_image erase firmware.hex` is also accepted and deliberately
performs a whole-bank erase first.

The standard flash path is automatically exercised against the Renode backend.
Physical PK4/ICD4 use still requires per-device qualification of address units,
programming-mode scripts, row alignment, erase mode, and configuration-memory
handling before it should be treated as production-ready.
