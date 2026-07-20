# TI C2000 Toolchain

> OpenOCD import note: this copy is a source-only tooling import. The generated
> `svd/` output, built `.vsix`, nested OpenOCD overlay, and per-tool Docker/CI
> scaffolding are intentionally excluded. See `OPENOCD_IMPORT.md`.

Unified SVD generation, VS Code debugging, Renode integration, and OpenOCD
XDS100v2/XDS100v3 support for selected TI C2000 and MSPM0 devices.

**Release:** `0.3.0`

## Supported devices

| Device/core | SVD | VS Code debug | Renode | OpenOCD/XDS100 |
|---|---:|---:|---:|---:|
| MSPM0C1103 | Yes | Cortex-Debug | No | Existing Arm target path |
| TMS320F28069 | Yes | `c2000-debug` | `custom-cores` | XDS100v2/v3 transport + C28x target integration |
| TMS320F280049 | Yes | `c2000-debug` | `custom-cores` | XDS100v2/v3 transport + C28x target integration |
| TMS320F28M35x C28x | Yes | `c2000-debug` | Platform still missing | XDS100v2/v3 transport + dual-core target integration |
| TMS320F28M35x Cortex-M3 | Yes | Cortex-Debug | Platform still missing | Standard Cortex-M3 OpenOCD path |

## Included components

### SVD and launch generator

`ti-svd` creates debugger-compatible CMSIS-SVD files and launch fragments.
MSPM0C1103 is sourced from the TI CMSIS pack. C2000 files are converted from
an installed CCS target database with explicit C28x word-to-byte address
normalization.

### VS Code extension

`extension/` contains the `c2000-debug` DAP extension. Backends:

- TI CCS Scripting for physical targets and XDS probes;
- Renode Monitor for the `xsession/renode:custom-cores` C2000 implementation;
- OpenOCD telnet for the custom C28x backend;
- deterministic mock backend for CI.

### OpenOCD XDS100 support

`openocd/` is a maintained overlay and semantic installer for the
`xsession/openocd` fork. It adds:

- XDS100v2 identities `0403:a6d0` and compatible `0403:6010`;
- XDS100v3 identity `0403:a6d1`;
- deterministic `PWR_RST` latch clearing before JTAG examination;
- runtime recovery after target-only power cycling;
- udev rules, scan-only tests, programmer wrappers, and C2000 examples.

The OpenOCD overlay is GPL-2.0-or-later. The rest of this repository is MIT
unless a file states otherwise.

## Repository layout

```text
bridge/                 CCS Scripting JSON bridge
devices/                Device source/address metadata
docs/                   Unified architecture and usage documentation
examples/renode/         Renode launch scripts
examples/vscode/         VS Code launch/task examples
extension/               c2000-debug extension source and VSIX
openocd/                 XDS100v2/v3 OpenOCD overlay, patcher, tests, docs
patches/                 Deterministic SVD corrections
reports/                 Renode and OpenOCD compatibility reports
scripts/                 Bootstrap, test, install, and release helpers
src/ti_svd/              SVD and launch-configuration CLI
svd/                     Generated SVD output directory
tests/                   Python generator tests
```

## Quick start

### Install the VS Code extension

```console
code --install-extension extension/c2000-debug-0.3.0.vsix
```

Also install:

```console
code --install-extension mcu-debug.peripheral-viewer
```

Use Cortex-Debug for MSPM0C1103 and the F28M35x M3 core.

### Generate SVD files

Windows:

```powershell
.\scripts\bootstrap.ps1
.\.venv\Scripts\ti-svd.exe discover --ccs-root C:\ti
.\.venv\Scripts\ti-svd.exe generate-all --ccs-root C:\ti
```

Linux/macOS:

```console
./scripts/bootstrap.sh
ti-svd discover --ccs-root "$HOME/ti"
ti-svd generate-all --ccs-root "$HOME/ti"
```

### Install XDS100 support into OpenOCD

Linux, macOS, Git Bash, or WSL:

```console
./scripts/install-openocd-xds100.sh /path/to/xsession/openocd
```

Windows PowerShell:

```powershell
.\scripts\install-openocd-xds100.ps1 -OpenOcdRoot C:\src\openocd
```

Then build OpenOCD with FTDI support:

```console
cd /path/to/xsession/openocd
./bootstrap
./configure --enable-ftdi --enable-internal-jimtcl --disable-werror
make -j"$(nproc)"
```

### Scan before programming

F28069 with XDS100v2:

```console
./openocd/scripts/test-xds100-openocd.sh \
  /path/to/openocd/src/openocd \
  v2 \
  target/ti/tms320f28069.cfg
```

F280049 with XDS100v3:

```console
./openocd/scripts/test-xds100-openocd.sh \
  /path/to/openocd/src/openocd \
  v3 \
  target/ti/tms320f280049.cfg
```

The scan-only test runs `init`, `scan_chain`, `targets`, and `shutdown`. It does
not erase or program flash.

### Program through OpenOCD

```console
./openocd/scripts/program-xds100.sh \
  /path/to/openocd/src/openocd \
  v2 \
  target/ti/tms320f28069.cfg \
  build/application.out
```

Actual C2000 erase/program capability depends on the custom C28x target and
flash backend in the selected OpenOCD checkout. XDS100 support supplies the USB,
FTDI, GPIO, and JTAG transport layer.

## VS Code backends

### CCS/XDS physical target

```jsonc
{
  "name": "F28069 via CCS",
  "type": "c2000-debug",
  "request": "launch",
  "backend": "ccs",
  "device": "tms320f28069",
  "ccsRoot": "C:/ti/ccs2040",
  "ccxml": "${workspaceFolder}/targetConfigs/F28069_XDS100v2.ccxml",
  "executable": "${workspaceFolder}/Debug/application.out",
  "svdPath": "${workspaceFolder}/svd/tms320f28069.svd",
  "addressScale": 2,
  "runToEntryPoint": "main"
}
```

### OpenOCD attach

Start OpenOCD first:

```console
openocd -f interface/ti/xds100v2.cfg \
  -f target/ti/tms320f28069.cfg
```

Then use:

```jsonc
{
  "name": "F28069 via OpenOCD/XDS100v2",
  "type": "c2000-debug",
  "request": "attach",
  "backend": "openocd",
  "device": "tms320f28069",
  "openocdHost": "127.0.0.1",
  "openocdTelnetPort": 4444,
  "svdPath": "${workspaceFolder}/svd/tms320f28069.svd",
  "addressScale": 2,
  "registerProfile": "c28x-fpu-vcu"
}
```

### Renode

```jsonc
{
  "name": "F28069 in Renode",
  "type": "c2000-debug",
  "request": "launch",
  "backend": "renode",
  "device": "tms320f28069",
  "renodePath": "C:/tools/renode/renode.exe",
  "renodeScript": "${workspaceFolder}/examples/renode/f28069.resc",
  "executable": "${workspaceFolder}/build/application.out",
  "svdPath": "${workspaceFolder}/svd/tms320f28069.svd",
  "addressScale": 2
}
```

## Build and test everything

```console
make test
make extension-package
make release
```

Or:

```console
./scripts/test-all.sh
```

Test groups:

- SVD conversion and launch generation;
- DAP, CCS bridge, mock, and Renode backends;
- XDS100 source transformation and idempotency;
- FTDI source fixture compilation;
- Tcl interface configuration validation;
- unified release archive integrity.

## Important hardware boundary

The repository can validate source transformations and debugger protocols
without hardware. It cannot prove physical C2000 halt, register access, flash
erase, or programming without the selected board, target configuration, probe,
and firmware image. Follow `docs/hardware-validation.md` and run scan-only checks
before any write operation.

See `docs/architecture.md`, `docs/openocd-xds100.md`, and
`docs/renode-custom-cores.md` for details.
