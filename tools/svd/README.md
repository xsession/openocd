# OpenOCD SVD Generator

`openocd_svd.py` is the repository-level entry point for CMSIS-SVD files. It
does not replace vendor-specific converters; it organizes them behind one CLI so
OpenOCD target configs, local SVD files, CMSIS-Pack imports, and generated TI
files can be checked the same way.

## Common Commands

List configured SVD sources and committed files:

```powershell
python .\tools\svd\openocd_svd.py list
```

Validate every committed SVD:

```powershell
python .\tools\svd\openocd_svd.py validate svd
```

Create an inventory report for OpenOCD target configs:

```powershell
python .\tools\svd\openocd_svd.py inventory --format markdown --out svd\catalog.md
```

Import all SVD files from a local CMSIS-Pack:

```powershell
python .\tools\svd\openocd_svd.py import-pack --pack C:\packs\Vendor.Device_DFP.1.0.0.pack --vendor vendor
```

Regenerate the TI SVD set from an installed CCS tree:

```powershell
python .\tools\svd\openocd_svd.py generate-ti --ccs-root C:\ti\ccs2100 --skip-fetch
```

## Address Units

The validator accepts SVD files that use 8-bit, 16-bit, or 32-bit address units.
This is needed for mixed OpenOCD support:

| Architecture | Native address unit | Debugger scaling |
|---|---:|---|
| Arm Cortex-M | 8 | byte-addressed |
| AVR | 8 | byte-addressed data/peripheral space |
| TI C2000 C28x | 16 | debugger must scale target addresses |
| Microchip dsPIC/PIC24 | 16 | debugger must scale target addresses |

Some vendor converters normalize SVD addresses to bytes and keep
`addressUnitBits` at 8. Others preserve the target's native address units.
Cortex-Debug launch files can use `memoryAddressUnitBytes` to match either
layout when its memory viewer talks to OpenOCD.
