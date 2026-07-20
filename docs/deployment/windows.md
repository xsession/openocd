# Windows package

The Windows package is cross-compiled in an Alpine container with MinGW-w64. It includes OpenOCD scripts and enabled adapter libraries.

## Build

From PowerShell, using Compose:

```powershell
docker compose -f docker/compose.yaml build windows-x86_64
docker compose -f docker/compose.yaml run --rm windows-x86_64
```

Using the helper script from Git Bash or WSL:

```console
$ ./docker/scripts/build-windows-cross.sh
```

Using Buildx directly:

```powershell
docker buildx build `
  --platform linux/amd64 `
  -f docker/Dockerfile.windows-cross `
  --target export `
  --output type=local,dest=artifacts/windows `
  .
```

## Output

```text
artifacts/windows/openocd-windows-x86_64.zip
```

The archive contains:

- `bin/openocd.exe`
- `bin/ftdi_eeprom.exe` when built by libftdi
- `share/openocd/scripts/`
- `openocd.cmd` convenience launcher

## Run

```powershell
Expand-Archive .\openocd-windows-x86_64.zip -DestinationPath C:\Tools\OpenOCD
C:\Tools\OpenOCD\openocd-windows-x86_64\openocd.cmd --version
```

Example probe/target command:

```powershell
.\openocd.cmd -f interface\cmsis-dap.cfg -f target\stm32f4x.cfg
```

Windows USB drivers must be compatible with libusb for adapters that use libusb. Vendor-native J-Link support follows the libjaylink/OpenOCD configuration included in the package.
