# Microchip PICkit 4

PICkit 4 support is split into three native OpenOCD paths:

- `pickit4` commands in `src/programmer/microchip/pickit4.c` for standalone
  RI4 programmer bring-up, USB probing, RI4 capability checks and chip erase.
- `programmer/microchip/pickit4-ri4.cfg` plus `target/mchp-ri4.cfg` for normal
  OpenOCD target and flash-bank workflows.
- `interface/microchip/pickit4-cmsis-dap.cfg` for target families and firmware
  modes that expose a standard CMSIS-DAP endpoint.

The old `programmer/microchip/pickit4.cfg` IPECMD bridge remains available as
a fallback for devices that still need MPLAB's proprietary programming stack.
