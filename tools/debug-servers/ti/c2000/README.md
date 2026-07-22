# TI C2000 OpenOCD Debug Server Wrapper

This folder contains the repo-local debug-server wrapper for TI C2000 targets,
with the F28M35x dual-core bring-up as the first validated workflow.

```text
GDB or Cortex-Debug
  -> OpenOCD GDB ports / monitor-only proxy ports
  -> c28x_openocd_wrapper.py
  -> OpenOCD scripts
  -> XDS100v2 / XDS100v3 / XDS110
  -> TI C2000 target
```

## Entry Points

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py preflight --preset f28m35x-dual-xds100v3
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py discover --preset f28m35x-dual-xds100v3 --elevate
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py server --preset f28m35x-dual-xds100v3 --elevate
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py gdb-monitor-proxy
```

Compatibility paths still work:

```powershell
python .\tools\support\c28x_openocd_wrapper.py preflight
python .\tools\support\tms320f28m35x_openocd_wrapper.py preflight
```

## External Dependencies

- OpenOCD binary, default packaged Windows path:
  `artifacts/windows/openocd-windows-x86_64/bin/openocd.exe`
- OpenOCD Tcl scripts from this repo or package.
- XDS100v2, XDS100v3, or XDS110 probe.
- Windows XDS100 driver binding when using XDS100:
  WinUSB/libusb-compatible driver on FTDI `MI_00`.
- GDB clients:
  `arm-none-eabi-gdb` for Cortex-M3 and monitor-only proxy workflows;
  a C28x-capable GDB/debug frontend for real C28x source debugging.

The wrapper does not vendor TI CCS, TI compiler tools, probe firmware, or
Windows USB driver packages beyond the OpenOCD packaging helpers already in the
tree.

## Local Vendor Runtime Extraction

To create a local, ignored copy of the TI CCS DebugServer runtime from an
installed CCS toolset:

```powershell
.\tools\debug-servers\ti\c2000\extract-ti-debug-server.ps1 -Force
```

This writes:

```text
tools/debug-servers/ti/c2000/vendor/ccs-debugserver-20.4.0/
```

The extracted folder includes `dslite-local.cmd`, `dbgjtag-local.cmd`,
`manifest.json`, `ccs_base/DebugServer`, `ccs_base/emulation`,
`ccs_base/common/bin`, `ccs_base/common/uscif`, and the selected
`ccs_base/common/targetdb` content.
The launchers set `TI_APPDATA_DIR` to an ignored local folder so DSLite does
not need to write to protected profile locations.

For a smaller C2000-focused extraction:

```powershell
.\tools\debug-servers\ti\c2000\extract-ti-debug-server.ps1 `
  -Force `
  -TargetDbMode C2000
```

Use the local tools directly:

```powershell
.\tools\debug-servers\ti\c2000\vendor\ccs-debugserver-20.4.0\dslite-local.cmd help
.\tools\debug-servers\ti\c2000\vendor\ccs-debugserver-20.4.0\dbgjtag-local.cmd -h
```

Probe identification through DSLite needs a CCS `.ccxml` file:

```powershell
.\tools\debug-servers\ti\c2000\vendor\ccs-debugserver-20.4.0\dslite-local.cmd `
  identifyProbe `
  --config path\to\your-board.ccxml
```

The C2000 extraction includes the F28M35x device XMLs and the
`TIXDS100v3_Dot7_Connection.xml` connection definition needed to build that
configuration in CCS.

The `vendor/` payload is ignored by git because it contains proprietary TI
files.

## Repo Dependencies

- `tcl/interface/ti/xds100v2.cfg`
- `tcl/interface/ti/xds100v3.cfg`
- `tcl/board/ti/tms320f28m35x-dual-core-xds100v2.cfg`
- `tcl/board/ti/tms320f28m35x-dual-core-xds100v3.cfg`
- `tcl/target/ti/tms320f28m35x-dual-core.cfg`
- `tcl/target/ti/c2000-icepick-scan.cfg`
- `docs/usage/tms320f28m35x-debug-findings.md`
- `docs/usage/vscode-f28m35x-dual-core.md`
- `examples/vscode/f28m35x-cortex-debug/`

## Ports

```text
OpenOCD M3 GDB              3333
OpenOCD C28x GDB            3334
OpenOCD TCL monitor         6666
Monitor-only M3 GDB proxy   3335
Monitor-only C28x GDB proxy 3336
```

## Current Validation

- C28x C2000 target detection works when OpenOCD can access XDS100v3.
- Safe dual-core config creates an examine-deferred M3 target and monitorable
  C28x target.
- The monitor-only GDB proxy allows Cortex-Debug/GDB to attach without
  programming and forward `monitor ...` commands.
- Real M3 source debug still requires the correct ICEPick route to the M3 DAP.
- Real C28x source debug still requires a C28x-capable GDB/debug backend.
