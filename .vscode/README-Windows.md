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
