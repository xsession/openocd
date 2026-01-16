# VS Code + Windows (MSYS2) build/debug

This workspace is set up to build OpenOCD with autotools into `build-vscode/` and debug the resulting `openocd.exe` from VS Code.

## 1) Install MSYS2

- Install MSYS2 to the default path: `C:\msys64`.
- Open **MSYS2 MinGW x64** (not the plain MSYS shell).

## 2) Install toolchain + common deps

Run in the MSYS2 MinGW x64 shell:

```sh
pacman -Syu
pacman -S --needed base-devel git autoconf automake libtool pkgconf \
  mingw-w64-x86_64-toolchain \
  mingw-w64-x86_64-libusb mingw-w64-x86_64-hidapi mingw-w64-x86_64-libftdi \
  mingw-w64-x86_64-capstone
```

(You may need additional optional deps depending on which adapter drivers you enable.)

## 3) Start VS Code from MSYS2 (recommended)

Starting VS Code from the MSYS2 shell ensures PATH contains MinGW tools:

```sh
code /e/GIT/openocd
```

If you start VS Code normally, the provided tasks still try to prepend `/mingw64/bin` to PATH, but launching from MSYS2 is more reliable.

## 4) Build

- Run **Terminal → Run Build Task** and pick `openocd: build (debug)`
- Output goes into `build-vscode/`

Notes:
- The VS Code `configure` task uses `--enable-internal-jimtcl` so you don't need a separate JimTcl install.
- The VS Code `configure` task enables SEGGER J-Link by building internal `libjaylink` (`--enable-internal-libjaylink --enable-jlink`).

## 5) Debug

- Press **F5**
- Choose **Debug OpenOCD (gdb, Windows .exe)**

Adjust the config passed to OpenOCD in `.vscode/launch.json` (the `-f board/...cfg` argument).

## 6) TI C2000 serial flashing (F28004x / F280049)

OpenOCD does not currently provide a C28x target + flash driver in this repo, so F280049 programming is wired up via TI's official C2000Ware **serial_flash_programmer.exe**.

- VS Code task: `ti: serial flash (F28004x/F280049)`
- Wrapper script: `tools/ti/flash_f28004x_serial.ps1`

The task prompts for:
- `COM` port (SCI bootloader)
- baud rate
- an **SCI boot format** app file (TI `.txt` image like the C2000Ware examples)

Prereqs:
- Install C2000Ware to `C:\ti\C2000Ware_5_03_00_00` (or edit the paths in `tools/ti/flash_f28004x_serial.ps1`).
- Put the device into the correct SCI boot mode and connect the UART.

### Optional: OpenOCD command backend (delegates to TI tool)

This repo also includes an **experimental** OpenOCD NOR flash backend named `ti_f28004x_serial`. It does not do native C28x/JTAG flash programming; it only provides an OpenOCD command path that runs TI's `serial_flash_programmer.exe`.

Example usage from an OpenOCD session (Telnet/Tcl):

```tcl
# Minimal dummy target (no JTAG)
target create ti.c2000 testee

# base/size/chip_width/bus_width are not used for real access here; size is only shown in 'flash info'
flash bank ti_f28004x_serial 0x0 0x80000 0 0 ti.c2000 COM7 9600 f28004x "C:/ti/C2000Ware_5_03_00_00/utilities/flash_programmers/serial_flash_programmer/serial_flash_programmer.exe" "C:/ti/C2000Ware_5_03_00_00/utilities/flash_programmers/serial_flash_programmer/kernels/F28004x_SCI_flash_kernels/SCI_flash_kernel.txt"

# Program an SCI-boot-format app image (.txt)
ti_f28004x_serial program 0 "C:/path/to/app_sci_boot.txt" COM7 9600
```

Notes:
- The `kernel` and `app` files must be TI SCI boot-format `.txt` images.
- If you omit the full path to `serial_flash_programmer.exe`, it must be on `PATH` when OpenOCD runs.
