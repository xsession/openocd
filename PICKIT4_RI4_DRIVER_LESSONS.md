# PICkit4 RI4 Native Driver: Lessons Learned

## Date: 2026-08-03

## Problem Statement

The OpenOCD native RI4 driver for PICkit4 could not communicate with target dsPIC33FJ128MC802 over ICSP. USB enumeration worked, side-channel scripts executed, but any script requiring target interaction (GetPC, EraseChip, ProgramMemory) blocked indefinitely on USB endpoint 0x83.

## Root Cause

A single 4-byte field in the RI4 USB protocol header — the **job_number** — was set to `0x00000000` instead of `0xFFFFFFFF`. This caused the PICkit4 firmware to reject all ICSP scripts, causing them to hang indefinitely waiting for a response that never came.

## Key Discoveries

### 1. The Critical Job Number Fix

```c
// BROKEN:
ri4_put_u32(buffer + 4, 0);

// FIXED:
ri4_put_u32(buffer + 4, 0xFFFFFFFF);  /* job_number */
```

This single change was the **root cause**. The PICkit4 firmware strictly requires `0xFFFFFFFF` as the job_number value. When `0` was sent, the device firmware silently dropped ICSP requests without generating an error, causing OpenOCD to wait indefinitely on the data channel.

**How we found it:** By writing a standalone libusb trace tool that sent the exact same request format as the Python reference implementation, with proper job_number. The trace showed GetPC returning valid PC values (0x00cf00cf), proving the hardware connection worked.

### 2. USB Initialization Sequence Matters

The driver was missing critical USB initialization steps that the Python reference implementation handles:

```c
// Required sequence:
libusb_set_configuration(dev, 1);
libusb_claim_interface(dev, 0);
libusb_set_interface_alt_setting(dev, 0, 0);  // Windows-specific!
libusb_clear_halt(dev, RI4_SIDE_OUT);
libusb_clear_halt(dev, RI4_SIDE_IN);
libusb_clear_halt(dev, RI4_DATA_OUT);
libusb_clear_halt(dev, RI4_DATA_IN);
```

- `libusb_set_interface_alt_setting()` is **critical on Windows** — without it, bulk endpoints don't activate
- `libusb_clear_halt()` on all endpoints resets any stuck endpoint state
- `libusb_reset_device()` **fails on Windows** — use `clear_halt()` instead

### 3. Scripting Engine Wake-Required

Before executing any scripts, send a GET_STATUS handshake to wake the PICkit4 scripting engine:

```c
uint8_t req[64];
ref_header(req, 261, 0xFFFFFFFF, (const uint8_t*)"Commands in progress", 19, 0);
send_side_channel(req, 35);  // 16 header + 19 bytes
```

This ensures the PICkit4 firmware is ready to accept script requests and drains any stale data on the endpoints.

### 4. Data Channel Draining

After GET_STATUS, check the `ocount` field in the response. If `ocount > 0`, drain that many bytes from the data channel (EP 0x83):

```c
uint32_t ocount = get_u32(reply + 12);
if (ocount > 0) {
    recv_data_channel(drain_buffer, ocount);
}
```

This consumes any pending data the PICkit4 is waiting for.

### 5. Recovery from Stuck States

When scripts block (e.g., target power loss), the only recovery is full USB reconnection:

```c
// 1. Send nuclear reset byte (0x86)
uint8_t nuclear = 0x86;
send_side_channel(&nuclear, 1);

// 2. Close USB handle
libusb_close(session->usb);
session->usb = NULL;

// 3. Wait for re-enumeration
sleep(500);

// 4. Re-find device
// 5. Re-open USB handle
// 6. Re-init endpoints
// 7. Re-send GET_STATUS
```

The nuclear reset causes the PICkit4 to USB-reenumerate, clearing all internal state. The driver must re-enumerate the device, reopen the handle, and re-initialize everything.

### 6. NULL Handle Guards

After failed recovery, `session->usb` can be NULL. Add guards in all bulk transfer functions:

```c
if (!session->usb)
    return ERROR_FAIL;
```

This prevents segfaults when recovery fails to reconnect.

### 7. Config Words Must Be Programmed

dsPIC33/PIC24 devices store configuration bits at **0x1F00000+** (not the
program memory range). Without config words, the chip won't start — oscillator,
watchdog, brown-out, and boot behavior are all controlled here. The HEX file
contains 8 config words that must be written with `WriteConfigmem` or `WriteDevCfg`
scripts, not `WriteProgmemPE`.

```c
/* Config memory on dsPIC33/PIC24 devices is at 0x1F00000+ */
if (address >= 0x1F00000) {
    static const char *const cfg_names[] = {"WriteConfigmem", "WriteDevCfg"};
    /* ... use config scripts instead of program memory scripts */
}
```

**How we found it:** Firmware was flashed and verified but the target didn't run
even after a power cycle. HEX analysis showed 8 config words at 0x1F00000-0x1F0001F
that the driver was silently skipping.

## What Did NOT Work

### Raw Power Scripts

The reference implementation uses "power scripts" (0x39, 0x46, 0x44, 0x40, 0x42, 0x43) to control target power. These caused full process hangs when implemented. Since the target was externally powered, they weren't needed.

### Target Power Negotiation

The reference has `SetSpeedFromDevice` and power enable steps. Our driver worked without explicit power control because the target board is externally powered. For self-powered PICkit4 configurations, these steps may be necessary.

## Debugging Methodology

### 1. Write Standalone USB Traces

Instead of debugging inside OpenOCD's complex runtime, write minimal libusb programs that:
- Send requests byte-for-byte matching the reference
- Log every byte sent/received
- Include hex dumps with protocol field parsing

This isolates the protocol from the framework.

### 2. Study the Reference Implementation

The Microchip open source Python implementation (`externals/open_microchip_tools/mchp_ri4/`) contains the exact protocol specification. Key files:

- `icd4_comms_usb.py` — USB communication layer
- `pk4_drv.py` — PICkit4 specific driver
- `transport.py` — Endpoint mapping and header format
- `commands.py` — RI4 command definitions
- `named_session.py` — Full session flow
- `power_control.py` — Power management scripts

### 3. Incremental Verification

Test each protocol element independently:
1. USB open + configuration
2. GET_STATUS handshake
3. Abort scripting engine
4. Named script execution (SCRIPT_NO_DATA)
5. Data upload/download (SCRIPT_UPLOAD/SCRIPT_DOWNLOAD)

### 4. The Trace Tool That Worked

```c
// Minimal working request format:
ref_header(req, msg_type, 0xFFFFFFFF, payload, len, transfer_len);
```

The 16-byte header:
- offset 0: msg_type (4 bytes LE)
- offset 4: job_number (4 bytes LE) = 0xFFFFFFFF
- offset 8: bcount = HEADER_SIZE + payload_len (4 bytes LE)
- offset 12: transfer_length (4 bytes LE)
- offset 16+: payload data

## Protocol Reference

### USB Endpoints (PICkit4 RI4 Mode)

| Direction | Endpoint | Purpose |
|-----------|----------|---------|
| OUT | 0x02 | Side channel commands |
| IN | 0x81 | Side channel responses |
| OUT | 0x04 | Data channel download |
| IN | 0x83 | Data channel upload |
| OUT | 0x03 | Streaming/debug traces |

### Command Types

| Type | Name | Description |
|------|------|-------------|
| 0x00000100 | SCRIPT_NO_DATA | Execute named script |
| 0xc0000101 | SCRIPT_DOWNLOAD | Download data to target |
| 0x80000102 | SCRIPT_UPLOAD | Upload data from target |
| 0x00000103 | SCRIPT_DONE | Mark script complete |
| 0x0000000d | RESULT | Response from device |
| 0x00000105 | GET_STATUS_FROM_KEY | Query status by key |
| 0x00000107 | ABORT_SCRIPTING_ENGINE | Abort all scripts |
| 0x00000110 | FLUSH_DATA_DOWNLOAD | Flush download buffer |
| 0x00000111 | FLUSH_DATA_UPLOAD | Flush upload buffer |
| 0x84 (single byte) | COMMAND_PROGRESS | Single-byte status check |
| 0x86 (single byte) | NUCLEAR_RESET | Hard reset + re-enumerate |

### Script Names

- `EnterDebugMode` — Enter ICSP debug mode
- `ExitDebugMode` — Exit debug mode
- `EnterTMOD_HV` — Enter high-voltage test mode
- `EnterTMOD_LV` — Enter low-voltage test mode
- `ExitTMOD` — Exit test mode
- `GetPC` — Read program counter
- `GetDeviceID` — Read device ID
- `EraseChip` — Erase entire device
- `WriteProgmemPE` — Write program memory (page erase)
- `ReadProgmemPE` — Read program memory
- `WriteConfigmem` — Write config words (addr >= 0x1F00000)
- `ReadConfigmem` — Read config words (addr >= 0x1F00000)
- `WriteDevCfg` — Alternate config write name
- `ReadDevCfg` — Alternate config read name
- `SetSpeedFromDevice` — Auto-negotiate ICSP speed

## Build Environment Notes

### Compiler Chain

- **Strawberry Perl gcc** for compilation: `/c/Strawberry/c/bin/gcc.exe`
- **MinGW64 gcc-ar** for archiving: `/c/msys64/mingw64/bin/gcc-ar`
- **MinGW64 gcc** for linking: `/c/msys64/mingw64/bin/gcc.exe`

The MinGW64 compiler fails with path mismatches (`D:/M/msys64` vs `C:/msys64`), but Strawberry Perl gcc works for C→O compilation. Link against MinGW64 libs (libusb, zlib, etc.).

### Include Path

Strawberry gcc needs Windows-style paths for MinGW64 headers:
```bash
/c/Strawberry/c/bin/gcc.exe -IC:/msys64/mingw64/include
```

MSYS-style paths (`/c/msys64/mingw64/include`) don't work with Strawberry gcc.

## Files Modified

- `src/target/mchp_ri4_native.c` — Core driver fixes
- `tcl/dspic33fj128MC802_pk4_direct.cfg` — Programming config
- `tcl/dspic33fj128MC802_pk4_test.cfg` — Test config

## Verification

The fix was verified by:
1. Standalone trace tool successfully read PC (0x00cf00cf)
2. Full firmware programming (~160KB) with verify pass
3. All write/verify cycles completed without errors
4. Target device examined successfully after programming

## Commit

`1c7422d64` — "mchp_ri4: fix PICkit4 native driver for dsPIC33FJ128MC802 programming"

## Lessons Summary

1. **Protocol headers matter** — A single 4-byte field caused all ICSP communication to fail
2. **Standalone tests win** — Minimal libusb traces isolate protocol from framework complexity
3. **Reference implementations are gold** — The Python reference contained the exact protocol spec
4. **USB quirks vary** — `libusb_reset_device()` fails on Windows; `clear_halt()` works
5. **Alt settings matter on Windows** — `libusb_set_interface_alt_setting()` activates bulk endpoints
6. **Recovery requires re-enumeration** — Nuclear reset causes USB re-enumeration; full reconnect needed
7. **Null guards prevent crashes** — Always check for NULL handles after recovery attempts