# TMS320F28M35x Debug Findings

This note records the local investigation of a TI TMS320F28M35x Concerto target
with an XDS100v3 probe, OpenOCD, TI Code Composer Studio 20.4.0, and
Cortex-Debug.

## Hardware And Probe Status

- Probe: TI XDS100v3, USB VID/PID `0403:A6D1`.
- OpenOCD board file: `tcl/board/ti/tms320f28m35x-xds100v3.cfg`.
- OpenOCD target file: `tcl/target/ti/tms320f28m35x.cfg`.
- Target model in OpenOCD: ICEPick router plus C28x target endpoint.
- Opt-in dual-core board file:
  `tcl/board/ti/tms320f28m35x-dual-core-xds100v3.cfg`.
- Opt-in dual-core target file:
  `tcl/target/ti/tms320f28m35x-dual-core.cfg`.

OpenOCD could initialize the target when run from an elevated Administrator
PowerShell:

```text
Info : clock speed 1000 kHz
Info : JTAG tap: tms320f28m35x.icepick tap/device found: 0x0b92902f
Info : [tms320f28m35x.c28x] Examination succeed
Info : [tms320f28m35x.c28x] starting gdb server on 3333
Info : Listening on port 3333 for gdb connections
```

The target list shown by OpenOCD was:

```text
TargetName          Type   Endian TapName                 State
tms320f28m35x.c28x  c28x   little tms320f28m35x.icepick   unknown
```

The C28x target could also be monitored through the OpenOCD TCL port after the
server was started:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py monitor targets poll reg
```

That returned the C28x target plus core registers such as `PC`, `SP`, `ACC`,
`ST0`, `ST1`, `XAR0` through `XAR7`, `IER`, `IFR`, `DBGIER`, and `RPC`.

The safe dual-core config also started one OpenOCD process with two GDB ports:

```text
Info : [tms320f28m35x.m3] starting gdb server on 3333
Info : [tms320f28m35x.c28x] starting gdb server on 3334
```

The same run listed:

```text
tms320f28m35x.m3    cortex_m  tms320f28m35x.m3tap     tap-disabled
tms320f28m35x.c28x  c28x      tms320f28m35x.icepick   unknown
```

When `F28M35X_M3_AUTO_ENABLE=1` was set, OpenOCD enabled
`tms320f28m35x.m3tap`, but M3 DAP examination failed with:

```text
Error: Invalid ACK (0) in DAP response
```

TAP-only scans of candidate ICEPick ports `0`, `1`, `2`, and `0x10` all read
M3 TAP IDCODE `0x00000000`, so the remaining issue is the exact TI
ICEPick/CS_DAP power or select sequence for the M3 route.

Alternate ICEPick-D-style and BDI-style route sequences were also tested for
candidate ports `0`, `1`, and `2`; all still enabled a zero-ID TAP rather than
the expected ARM CoreSight ID `0x4ba00477`.

## Windows Driver Findings

The XDS100v3 debug interface must be accessible through libusb for OpenOCD.
The packaged helper installed WinUSB for FTDI interface MI_00 only.

Observed Windows driver binding after installation:

```text
MI_00: XDS100v3 Debug Port (WinUSB), provider libwdi
MI_01: XDS100v3 Class Auxiliary Port, provider Texas Instruments
```

This is the correct split for OpenOCD:

- MI_00 is the debug/JTAG interface and should be WinUSB for OpenOCD.
- MI_01 is the auxiliary port and should remain on the TI/vendor driver.

OpenOCD still failed from a non-elevated shell with libusb errors, but worked
when launched as Administrator. That points to a remaining Windows access/session
issue rather than an OpenOCD target configuration issue.

## OpenOCD C28x Status

The local OpenOCD configuration successfully:

- Loaded the XDS100v3 FTDI adapter configuration.
- Selected JTAG.
- Created the ICEPick TAP.
- Created a C28x target.
- Examined the C28x endpoint.
- Started a GDB server on port `3333`.

The OpenOCD target configuration uses:

```tcl
c28x device F28M35x-C28x
c28x procid 0x5000A3F8
c28x icepick_port 0x11
c28x gel_file ../../emulation/gel/f28m35h52c1_c28.gel
```

The C28x ICEPick port found in TI CCS target database also matches `0x11`.

## GDB And Cortex-Debug Findings

The available ARM GDB was:

```text
C:\arm-none-eabi\11_3\bin\arm-none-eabi-gdb.exe
```

It could connect to OpenOCD far enough to receive the target description, but it
could not debug the C28x core:

```text
warning: while parsing target description: Target description specified unknown architecture "c28x"
warning: Could not load XML target description; ignoring
Truncated register 16 in remote 'g' packet
"monitor" command not supported by this target.
```

Conclusion: Cortex-Debug cannot debug the C28x core with `arm-none-eabi-gdb`.
A C28x-capable GDB would be required for a GDB/Cortex-Debug workflow, but no such
binary was found in the installed TI folders.

## TI C2000 Toolchain Search

The requested compiler directory exists:

```text
C:\ti\ccs2040\ccs\tools\compiler\ti-cgt-c2000_22.6.3.LTS\bin
```

It contains classic TI C2000 code generation tools, including:

```text
cl2000.exe
asm2000.exe
lnk2000.exe
hex2000.exe
nm2000.exe
ofd2000.exe
dis2000.exe
strip2000.exe
```

It does not contain:

```text
c28x-gdb.exe
c2000-gdb.exe
gdb.exe
```

The TI CGT C2000 toolchain therefore cannot be used as the GDB executable for
Cortex-Debug.

## TI CCS Debug Architecture

The installed CCS 20.4.0 tree shows that TI C2000 debugging uses TI Debug Server
and target database XML files, not GNU GDB.

Important local files:

```text
C:\ti\ccs2040\ccs\ccs_base\DebugServer\bin\DSLite.exe
C:\ti\ccs2040\ccs\ccs_base\DebugServer\bin\DebugServer.dll
C:\ti\ccs2040\ccs\ccs_base\scripting\bin\dss.bat
C:\ti\ccs2040\ccs\scripting\run.bat
C:\ti\ccs2040\ccs\ccs_base\common\uscif\dbgjtag.exe
C:\ti\ccs2040\ccs\ccs_base\common\uscif\gdb_agent_console.exe
```

`gdb_agent_console.exe` exists, but its help output only advertised MSP430/MSP432
style GDB-agent usage and MSP432 flash options. It did not indicate C2000/C28x
GDB support.

The CCS C28x architecture definition is:

```text
C:\ti\ccs2040\ccs\ccs_base\common\targetdb\cpus\c28xx.xml
```

It identifies the CPU as:

```xml
<cpu id="TMS320C28XX" isa="TMS320C28XX" desc="C28xx" description="C28xx CPU">
```

The F28M35H52C1 device description is:

```text
C:\ti\ccs2040\ccs\ccs_base\common\targetdb\devices\f28m35h52c1.xml
```

Relevant values from that file:

```text
M3 subpath port:   0x10
C28x subpath port: 0x11
C28x ISA:          TMS320C28XX
C28x GEL:          ../../emulation/gel/f28m35h52c1_c28.gel
```

The XDS100 C28x driver XML files are:

```text
C:\ti\ccs2040\ccs\ccs_base\common\targetdb\drivers\tixds100c28x.xml
C:\ti\ccs2040\ccs\ccs_base\common\targetdb\drivers\tixds100v2c28x.xml
```

They point to the proprietary TI driver:

```text
C:\ti\ccs2040\ccs\ccs_base\emulation\drivers\tixds28x.dvr
```

with:

```xml
<isa Type="TMS320C28XX" ProcID="0x5000A3F8">
```

The XDS100v3 connection definition is:

```text
C:\ti\ccs2040\ccs\ccs_base\common\targetdb\connections\TIXDS100v3_Dot7_Connection.xml
```

It identifies the connection as:

```xml
<connection desc="Texas Instruments XDS100v3 USB Debug Probe"
            id="Texas Instruments XDS100v3 USB Emulator">
```

and uses:

```xml
<connectionType Type="TIXDS100v2"/>
```

This means CCS treats XDS100v3 as an XDS100v2-style debug connection with
additional dot7/XDS100v3 connection properties.

## CCS `.ccxml` Findings

Sample F28M35H52C1 target configuration files were found:

```text
C:\ti\ccs2040\ccs\ccs_base\scripting\examples\uniflash\configs\F28M35H52C1_Serial.ccxml
C:\ti\ccs2040\ccs\ccs_base\scripting\examples\uniflash\configs\F28M35H52C1_XDS560.ccxml
```

No ready-made F28M35H52C1 XDS100v3 `.ccxml` was found. A CCS-side XDS100v3
configuration would need to combine:

- `connections\TIXDS100v3_Dot7_Connection.xml`
- `devices\f28m35h52c1.xml`
- C28x subpath port `0x11`
- M3 subpath port `0x10`
- C28x GEL file `f28m35h52c1_c28.gel`
- M3 GEL file `f28m35h52c1_m3.gel`

## Practical Conclusions

1. OpenOCD can see and examine the F28M35x C28x target through XDS100v3 when run
   elevated.
2. The current OpenOCD path exposes the C28x target through a GDB server on
   port `3333`.
3. ARM GDB cannot debug the C28x core because it does not understand the `c28x`
   architecture/register packet.
4. The installed TI C2000 compiler is not a GDB toolchain.
5. TI CCS uses TI Debug Server, targetdb XML, `.ccxml`, GEL, and `tixds28x.dvr`
   for C28x debugging.
6. Cortex-Debug can only be viable for C28x if a C28x-capable GDB or a new
   adapter backend for TI Debug Server is provided.
7. Switching MI_00 to WinUSB helps OpenOCD, but may prevent TI CCS/XDS tools
   from seeing the same probe until the TI driver binding is restored.

## OpenOCD Wrapper

The repository includes a generic C28x OpenOCD-side convenience wrapper:

```text
tools/debug-servers/ti/c2000/c28x_openocd_wrapper.py
```

It makes the OpenOCD side look like a stable, ordinary external GDB server by
choosing a known C28x board preset or a user-supplied OpenOCD config file,
stabilizing the ports, waiting for readiness, and offering an OpenOCD monitor
client. It does not translate the C28x
architecture into ARM or another GDB architecture.

Built-in presets:

```text
f28m35x-xds100v3
f28m35x-dual-xds100v3
f28069-xds100v3
f280049-xds100v3
```

Run local checks:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py preflight --preset f28m35x-xds100v3
```

Probe once:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py probe --preset f28m35x-xds100v3 --elevate
```

Run safe ICEPick/JTAG discovery:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py discover --preset f28m35x-xds100v3 --elevate
```

Start the OpenOCD server:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py server --preset f28m35x-xds100v3 --elevate
```

Start the opt-in dual-core OpenOCD server:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py server --preset f28m35x-dual-xds100v3 --elevate
```

Intentionally test the M3 route:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py probe --preset f28m35x-dual-xds100v3 --set F28M35X_M3_AUTO_ENABLE=1 --elevate
```

If OpenOCD is already running, send monitor commands through the TCL port:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py monitor targets poll
```

Generate a Cortex-Debug external-server template:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py cortex-debug-json --preset f28m35x-xds100v3
```

Use another C28x board file without adding a preset:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py server --board board/ti/my-c28x-board.cfg --elevate
```

The generated Cortex-Debug template still requires a GDB executable that
understands C28x. With `arm-none-eabi-gdb`, the session will still fail when GDB
parses the `c28x` target description and register packet.

## VS Code Dual-Core Example

The user-facing VS Code example is:

```text
examples/vscode/f28m35x-cortex-debug/
```

It contains:

- `tasks.json` for preflight, ICEPick discovery, OpenOCD server start, C28x
  monitor snapshot, and shutdown.
- `launch.json` with the intended Cortex-M3 plus C28x compound launch shape.
- `README.md` describing the current working monitor path and the remaining
  requirements for simultaneous two-core source debugging.

Current practical status:

- C28x detection and monitoring through OpenOCD is working when OpenOCD can
  access the XDS100v3.
- Cortex-M3 source debugging through Cortex-Debug can use the opt-in dual-core
  OpenOCD config after the M3 TAP route is validated on the real board.
- C28x source debugging through Cortex-Debug needs the local Cortex-Debug patch
  plus a C28x-capable GDB/debug backend.

## Fresh Cortex-Debug Live Attach Test

The local Cortex-Debug submodule was rebuilt with:

```powershell
cd .\tools\vscode\cortex-debug
npm.cmd ci
npm.cmd run compile
```

The build generated fresh `dist/extension.js` and `dist/debugadapter.js`.

Then one live OpenOCD server was started without programming the target:

```powershell
.\artifacts\windows\openocd-windows-x86_64\bin\openocd.exe `
  -s .\tcl `
  -f board/ti/tms320f28m35x-dual-core-xds100v3.cfg `
  -c "adapter speed 1000"
```

OpenOCD started both GDB services:

```text
tms320f28m35x.m3    GDB localhost:3333
tms320f28m35x.c28x  GDB localhost:3334
```

Attach-only GDB monitor tests, matching the transport path Cortex-Debug uses
for `servertype: external`, were run without `load`, `program`, flash, or reset
commands.

M3 result:

```text
Target tms320f28m35x.m3, state: examine deferred
Target not examined yet, refuse gdb connection
```

C28x result with the available ARM GDB:

```text
Target description specified unknown architecture "c28x"
Truncated register 16 in remote 'g' packet
```

The same live OpenOCD process was monitorable through the TCL monitor:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py monitor targets poll reg
```

That returned both target entries and the C28x register list. Therefore the
working live "monitor both" path today is OpenOCD TCL monitor, not Cortex-Debug
GDB attach. Cortex-Debug becomes usable for the M3 session once the M3 DAP
examines successfully, and for C28x once a C28x-capable GDB/debug backend is
available.

## Monitor-Only GDB Proxy

The wrapper now includes a monitor-only GDB/RSP proxy for Cortex-Debug and
ordinary GDB clients:

```powershell
python .\tools\debug-servers\ti\c2000\c28x_openocd_wrapper.py gdb-monitor-proxy
```

Default ports:

```text
M3 monitor proxy    localhost:3335
C28x monitor proxy  localhost:3336
OpenOCD TCL monitor localhost:6666
```

This proxy fixes the Cortex-Debug monitor attach failure mode by giving GDB a
minimal safe RSP endpoint and forwarding `monitor ...` commands to OpenOCD's TCL
monitor. It intentionally does not implement C28x source debugging, M3 DAP
bring-up, memory access, breakpoints, reset, halt, or stepping.

The matching VS Code example is:

```text
examples/vscode/f28m35x-cortex-debug
```

Use compound launch `F28M35x: monitor both cores, no programming` after the
OpenOCD server and the proxy task are running.

## Current Live USB Failure

On the latest local check, OpenOCD could not open the XDS100v3 because Windows
did not report a connected `VID_0403&PID_A6D1` device. The connected nearby FTDI
device was:

```text
USB\VID_0403&PID_6014\210299A07070
Device Description: Digilent USB Device
```

That is not the XDS100v3 USB ID expected by `interface/ti/xds100v3.cfg`. The
wrapper preflight now reports this explicitly before OpenOCD is started.

## Useful References

- TI CCS Debug Overview:
  https://software-dl.ti.com/ccs/esd/documents/users_guide_ccs_20.1.1/ccs_debug-main.html
- TI CCS Scripting:
  https://software-dl.ti.com/ccs/esd/documents/users_guide_ccs_20.2.0/ccs_debug-scripting.html
