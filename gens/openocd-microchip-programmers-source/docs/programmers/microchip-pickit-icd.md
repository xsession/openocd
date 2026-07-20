# Microchip PICkit and ICD programmer integration

This tree adds an OpenOCD command surface for production-style programming with
these Microchip tools:

| Programmer | Default backend | PIC/dsPIC programming | Standard CMSIS-DAP adapter config |
|---|---|---:|---:|
| PICkit 2 | `pk2cmd` | Yes, when the device exists in `PK2DeviceFile.dat` | No |
| PICkit 3 | MPLAB IPECMD | Yes | No |
| PICkit 4 | MPLAB IPECMD | Yes | `interface/microchip/pickit4-cmsis-dap.cfg` |
| MPLAB ICD 4 | MPLAB IPECMD | Yes | `interface/microchip/icd4-cmsis-dap.cfg` |

## Architecture and scope

PIC and dsPIC programming is not a standard JTAG/SWD flash algorithm. The
programming sequences are device-family scripts interpreted by Microchip's
tools. OpenOCD therefore provides the configuration, validation and command
surface, while a supported external programming engine executes the ICSP
sequence:

- `pk2cmd` for PICkit 2 and for PICkit 3 running legacy scripting firmware;
- MPLAB IPECMD for PICkit 3, PICkit 4 and ICD 4;
- optionally `pymcuprog` for PICkit 4 in AVR/CMSIS-DAP mode.

No non-free `pk2cmd` code or Microchip device database is copied into OpenOCD.
Install the selected backend separately and accept its license terms.

The PICkit 4 and ICD 4 interface files are a separate direct CMSIS-DAP path for
target families and tool modes that expose a standard JTAG/SWD endpoint. They
do not turn PIC/dsPIC ICSP into CMSIS-DAP.

## Installed OpenOCD files

```text
scripts/programmer/microchip/pickit2.cfg
scripts/programmer/microchip/pickit3.cfg
scripts/programmer/microchip/pickit4.cfg
scripts/programmer/microchip/icd4.cfg
scripts/interface/microchip/pickit4-cmsis-dap.cfg
scripts/interface/microchip/icd4-cmsis-dap.cfg
```

## Backend installation

### PICkit 2 and legacy PICkit 3

Install `pk2cmd` and its matching `PK2DeviceFile.dat`. Set the executable with
one of:

```sh
export PK2CMD=/absolute/path/to/pk2cmd
```

or:

```tcl
microchip executable /absolute/path/to/pk2cmd
```

PICkit 3 must contain the scripting firmware expected by `pk2cmd`. Switching
back to MPLAB may replace that firmware.

### PICkit 3, PICkit 4 and ICD 4

Install MPLAB X/IPE and point OpenOCD to IPECMD:

```sh
export IPECMD="/opt/microchip/mplabx/v6.25/mplab_platform/mplab_ipe/ipecmd.sh"
```

On Windows:

```text
C:\Program Files\Microchip\MPLABX\v6.25\mplab_platform\mplab_ipe\ipecmd.exe
```

The exact MPLAB X version and executable name can differ. Use
`microchip executable` when automatic PATH lookup is not sufficient.

## Programming examples

PICkit 4 and a dsPIC33 target:

```sh
openocd -f programmer/microchip/pickit4.cfg \
  -c "microchip device dsPIC33EP128GM604" \
  -c "microchip executable /opt/microchip/mplabx/v6.25/mplab_platform/mplab_ipe/ipecmd.sh" \
  -c "microchip program build/firmware.hex" \
  -c shutdown
```

ICD 4 with a specific serial number:

```sh
openocd -f programmer/microchip/icd4.cfg \
  -c "microchip device dsPIC33FJ128MC804" \
  -c "microchip serial BUR123456789" \
  -c "microchip program build/firmware.hex" \
  -c shutdown
```

PICkit 2:

```sh
openocd -f programmer/microchip/pickit2.cfg \
  -c "microchip device dsPIC30F5011" \
  -c "microchip program build/firmware.hex" \
  -c shutdown
```

PICkit 3 using legacy `pk2cmd` instead of IPECMD:

```sh
openocd -f programmer/microchip/pickit3.cfg \
  -c "microchip backend pk2cmd" \
  -c "microchip device dsPIC33FJ128MC802" \
  -c "microchip program build/firmware.hex" \
  -c shutdown
```

Preview the exact external command without touching hardware:

```sh
openocd -f programmer/microchip/pickit4.cfg \
  -c "microchip device dsPIC33EP128GM604" \
  -c "microchip dry_run on" \
  -c "microchip program build/firmware.hex" \
  -c shutdown
```

## Configuration commands

```text
microchip programmer pickit2|pickit3|pickit4|icd4
microchip backend auto|pk2cmd|ipecmd|pymcuprog
microchip device <part>
microchip executable auto|<path>
microchip serial none|<serial>
microchip vdd external|off|<voltage>
microchip erase_before_program on|off
microchip verify_after_program on|off
microchip release_reset on|off
microchip working_directory none|<path>
microchip pack_path none|<DFP path>
microchip interface none|<interface>
microchip clock none|<Hz>
microchip verbose on|off
microchip dry_run on|off
microchip show
microchip command <action> [firmware.hex]
microchip program <firmware.hex>
microchip erase
microchip verify <firmware.hex>
```

Programming defaults to erase, program, verify and release from reset.
`microchip vdd external` is the safe default; OpenOCD does not enable target
power unless an explicit voltage is configured.

## `pymcuprog` mode

`pymcuprog` is available only as an explicit PICkit 4 backend:

```sh
openocd -f programmer/microchip/pickit4.cfg \
  -c "microchip backend pymcuprog" \
  -c "microchip device avr128da48" \
  -c "microchip interface updi" \
  -c "microchip program app.hex" \
  -c shutdown
```

This path is intended for the tool's AVR/CMSIS-DAP mode. It is not the general
PIC/dsPIC backend. PIC targets may additionally require a Device Family Pack
specified by `microchip pack_path`.

## Linux permissions

The supplied `contrib/60-openocd.rules` contains rules for:

```text
04d8:0033  PICkit 2
04d8:900a  PICkit 3 scripting mode
03eb:2177  PICkit 4 CMSIS-DAP/HID
03eb:217c  ICD 4 CMSIS-DAP/HID
```

Install and reload the rules:

```sh
sudo cp contrib/60-openocd.rules /etc/udev/rules.d/60-openocd.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then unplug and reconnect the programmer.

## Direct CMSIS-DAP usage

For an ARM target supported by the probe firmware:

```sh
openocd \
  -f interface/microchip/pickit4-cmsis-dap.cfg \
  -f target/<target>.cfg
```

This direct adapter path uses OpenOCD's existing CMSIS-DAP driver and does not
invoke IPECMD.
