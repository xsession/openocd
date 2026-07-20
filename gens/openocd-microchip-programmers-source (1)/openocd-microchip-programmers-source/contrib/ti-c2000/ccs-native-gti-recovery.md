# CCS native GTI/TRG recovery notes for C28x

This note records the sanitized CCS-native information used by the OpenOCD C28x backend. It intentionally records operation IDs, command names, packet-shape notes, and data provenance only; it does not include proprietary decompiled TI source.

## Source material

The values below were recovered from a locally supplied CCS `ccs_base` tree:

- `emulation/drivers/tixds28x.dvr`
- `common/uscif/jscxds110.dll`
- `common/uscif/xdsfast3.dll`
- Java DSS and memory-server JARs inspected through manifests, class lists, and `javap` output
- C28x register-ID XML files under the CCS DebugServer/device database

## Native C28x GTI exports

`tixds28x.dvr` exports the C28x-facing GTI entry points that CCS uses for target control:

- `GTI_HALT`
- `GTI_RUN`
- `GTI_STEP`
- `GTI_STAT`
- `GTI_READREG`
- `GTI_WRITEREG`
- `GTI_READMEM`
- `GTI_WRITEMEM`
- `GTI_CONNECT`
- `GTI_INIT_EX`
- `TRG_call`
- `TRG_check`
- `TRG_connect`

## Recovered TRG operation IDs

| Operation | ID | Observed source path |
|---|---:|---|
| register read | `0x05` | `GTI_READREG -> TRG_call(0x05)` |
| register write | `0x06` | `GTI_WRITEREG -> TRG_call(0x06)` |
| run/resume | `0x0d` | `GTI_RUN -> helper -> TRG_call(0x0d)` |
| single step | `0x0e` | `GTI_STEP -> TRG_call(0x0e)` |
| halt | `0x0f` | `GTI_HALT -> TRG_call(0x0f)` |
| free-run variant | `0x16` | run-family path |
| run-to-address variant | `0x17` | run-family path |
| block memory read | `0x41` | `GTI_READMEM -> TRG_call(0x41)` |
| block memory write | `0x42` | `GTI_WRITEMEM -> TRG_call(0x42)` |
| status/preflight | `0x5a` | run/status preflight path |

## Recovered flags

| Flag | Value | Observed use |
|---|---:|---|
| realtime mode | `1 << 15` | halt and step paths |
| single-step mode | `1 << 12` | step path |
| force-run/run-mode | `1 << 16` | run-family path |

## XDS110 C28x command IDs

`jscxds110.dll` exposes C28x memory helpers and string/constant recovery found:

| Name | ID |
|---|---:|
| `C28X_MEMREAD` | `0x33` |
| `C28X_MEMWRITE` | `0x34` |

## OpenOCD exposure

The backend exposes this recovered metadata with:

```tcl
c28x gti all
c28x gti ops
c28x gti flags
c28x gti xds110
```

The backend still keeps low-level execution paths fail-closed unless the transport implementation can send the matching C28x/XDS transaction on the active adapter. This avoids pretending that raw JTAG scan operations are equivalent to TI's private native GTI transport.
