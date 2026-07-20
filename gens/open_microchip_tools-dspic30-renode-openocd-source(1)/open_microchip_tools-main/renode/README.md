# Renode custom-core validation

The OpenOCD bridge can use either a physical PICkit/ICD RI4 session or the GDB
server in `xsession/renode`'s `custom-cores` branch. The Renode backend provides
deterministic tests of flash, erase, verify, memory access, run/halt/step, PC
access, hardware breakpoints, and read/write/access watchpoints without USB
hardware.

## Supported custom-core profiles

| Core | Renode PC register | PC width | Emulated flash range | Default data/watch range |
|---|---:|---:|---:|---:|
| PIC16 | 1 | 2 bytes | `0x000000..0x003FFF` | `0x200000` |
| PIC18 | 3 | 4 bytes | `0x000000..0x01FFFF` | `0xA00000` |
| dsPIC30F5011 | 16 | 4 bytes | sysbus `0x100000..0x10ABFF` | `0x001000` |
| dsPIC33 | 16 | 4 bytes | `0x000000..0x03FFFF` | unified memory |

`DSPIC30F` family names are recognized by the bridge. The checked-in custom
Renode branch currently provides a concrete `dsPIC30F5011` CPU/platform model,
so that is the default no-hardware qualification target. Other dsPIC30 devices
can reuse the architecture path only after supplying the correct Renode memory
and peripheral platform and overriding flash geometry where it differs.

## 1. Build the custom Renode branch

```bash
git clone --recursive --branch custom-cores https://github.com/xsession/renode.git
cd renode
./build.sh --no-gui
```

For an existing checkout:

```bash
git submodule update --init --recursive
```

## 2. Start a blank emulated target

Start Renode in console/headless mode:

```bash
./renode --console --disable-gui
```

Then include one platform script from this repository:

```text
include @/absolute/path/to/open_microchip_tools/renode/platforms/pic18_openocd.resc
```

Use `pic16_openocd.resc`, `dspic30_openocd.resc`, or
`dspic33_openocd.resc` for the other cores. The
script opens the Renode GDB server on port 3333 without autostart. The Python
backend sends `monitor start` after attaching, before continue or step.

## 3. Validate the backend directly

```bash
python -m mchp_renode_cosim.validation \
  --core pic18 \
  --host 127.0.0.1 \
  --port 3333 \
  --firmware /path/to/blink_pic18.bin
```

The validator accepts `.bin`, `.hex`, `.ihex`, or `.elf`. It executes erase,
program, verify, PC read/write, breakpoint insertion/removal, all three
watchpoint modes, single-step, asynchronous run/halt, and reset.

For dsPIC30F5011:

```bash
python -m mchp_renode_cosim.validation \
  --core dspic30 \
  --host 127.0.0.1 \
  --port 3333 \
  --firmware /path/to/firmware.hex
```

Normal dsPIC30 firmware images use logical code addresses starting at zero.
The Renode platform maps that storage at sysbus `0x100000`; the direct
validator translates image segments into that window and accepts already
rebased images without applying the offset twice.

## 4. Run through OpenOCD

Install and build the overlay-enabled OpenOCD:

```bash
python openocd/install_overlay.py /path/to/openocd
cd /path/to/openocd
./bootstrap
./configure --enable-dummy
make -j
```

Start the bridge in a second terminal:

```bash
python -m mchp_openocd.bridge_server \
  --backend renode \
  --renode-host 127.0.0.1 \
  --renode-port 3333 \
  --host 127.0.0.1 \
  --port 9123
```

Start the integrated OpenOCD target in a third terminal:

```bash
/path/to/openocd/src/openocd \
  -s /path/to/open_microchip_tools/openocd/overlay/tcl \
  -c "set MCHP_RI4_HOST 127.0.0.1" \
  -c "set MCHP_RI4_PORT 9123" \
  -c "set MCHP_RENODE_PROCESSOR PIC18" \
  -f target/mchp-renode.cfg
```

Standard OpenOCD commands:

```text
init
halt
flash info 0
flash erase_sector 0 0 last
flash write_image /absolute/path/firmware.hex
verify_image /absolute/path/firmware.hex
reg pc
step
bp 0x100 2 hw
rbp 0x100
wp 0xA00010 1 w
rwp 0xA00010
resume
halt
reset halt
```

For a dsPIC30 logical-address image when entering commands manually, use:

```text
flash write_image /absolute/path/firmware.hex 0x100000
verify_image /absolute/path/firmware.hex 0x100000
```

Compatibility commands remain available for direct bridge diagnosis:

```text
mchp_ri4 capabilities mchp.cpu
mchp_ri4 erase mchp.cpu
mchp_ri4 program mchp.cpu /absolute/path/firmware.hex verify
mchp_ri4 verify mchp.cpu /absolute/path/firmware.hex
```

## Automated three-process test

After Renode and OpenOCD have been built, run:

```bash
python renode/run_openocd_e2e.py \
  --renode /path/to/renode/renode \
  --openocd /path/to/openocd/src/openocd \
  --core pic18 \
  --firmware /path/to/blink_pic18.bin
```

Use `--core dspic30` for the dsPIC30F5011 path. The harness examines the image
addresses and adds the OpenOCD `0x100000` offset only when required.

The harness launches Renode, the Python bridge, and OpenOCD. It uses the
standard flash bank for erase/write/verify, then exercises PC access, stepping,
memory access, breakpoints, watchpoints, asynchronous resume/halt, and reset.
Separate logs are stored under `renode-openocd-logs/`.
