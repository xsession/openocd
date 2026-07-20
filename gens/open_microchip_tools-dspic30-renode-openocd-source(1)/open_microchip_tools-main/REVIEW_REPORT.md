# Review and refactor report

## Critical findings fixed

1. **Test collection/runtime failure on current Python** — `IpecmdServer.backend`
   used a mutable dataclass instance as a default. It now uses
   `field(default_factory=StubBackend)`.
2. **Misleading OpenOCD proof of concept** — the historical patch only changed
   local OpenOCD state for halt/resume/step and omitted real memory, reset,
   flash, breakpoint, and watchpoint behavior. `openocd/overlay/` is now the
   maintained implementation and the old patch is explicitly obsolete.
3. **No hardware-free target backend** — the JSON bridge now supports the GDB
   server in `xsession/renode:custom-cores`, with PIC16, PIC18, dsPIC30, and dsPIC33
   profiles for PC register index/width, flash range, reset, and watchpoint
   behavior.
4. **No standard OpenOCD flash integration** — a registered NOR driver named
   `mchp_ri4` now maps the normal OpenOCD erase/write/read/verify callbacks to
   the shared bridge target. Renode target files create the bank automatically.
5. **Invalid target creation on current OpenOCD** — current non-DAP target
   creation requires a chain position. The configuration now creates a virtual
   TAP, uses the dummy adapter, and suppresses physical JTAG initialization and
   reset scans because all actual traffic is delegated to the JSON bridge.
6. **Unsafe target-type identity check** — OpenOCD copies `struct target_type`
   per target, so comparing `target->type` to the global driver object by
   pointer is invalid. The bridge now validates the registered type name.
7. **Incorrect installer source path** — the standalone installer generated an
   extra `target/` path for current `src/target/Makefile.am` layouts. It now
   recognizes both current and legacy layouts.
8. **Incomplete installer registration** — installation now copies and
   registers the target C/header, NOR flash driver, interface/target Tcl files,
   target type, and flash driver in all required OpenOCD build/driver tables.

## Functional assessment

| Function | RI4/PICkit implementation | Renode backend coverage | Physical qualification |
|---|---|---:|---:|
| Standard OpenOCD flash bank | Registered `mchp_ri4` NOR driver | Yes | Required |
| Flash/program image | RI4 program-memory scripts | Yes, memory-backed | Required |
| Whole-bank erase | Family-profile erase scripts | Yes, fill with `0xFF` | Required |
| Read-back verify | Program-memory comparison | Yes, mismatch reporting | Required |
| Halt/resume/step | Real bridge commands | Yes, asynchronous GDB RSP | Required |
| Status polling | Capability-driven `targetStatus` | Yes | Required |
| PC read/write | RI4 GetPC/SetPC where available | Yes, per-core register map | Required |
| Program-memory read/write | RI4 scripts | Yes | Required |
| Hardware breakpoints | `SetHWBP`/`ClearHWBP` when exposed | Yes, GDB `Z1`/`z1` | Required |
| Read/write/access watchpoints | Device-pack data-BP scripts | Yes, GDB `Z2`-`Z4` | Required |
| Reset | RI4 reset/debug scripts | Renode machine reset + reset-PC restore | Required |

The implementation reports unsupported functions when a selected MPLAB device
pack lacks the required scripts. It does not pretend every MCU family has the
same breakpoint, watchpoint, memory, or flash geometry.

## Renode/OpenOCD validation path

The repository includes:

- `mchp_renode_cosim.gdb_session`: stateful PIC16/PIC18/dsPIC30/dsPIC33 GDB backend;
- `mchp_renode_cosim.validation`: direct erase/program/verify/debug validator;
- `renode/platforms/*_openocd.repl` and `.resc`: blank custom-core targets;
- `target/mchp-renode.cfg`: automatic profile/flash-bank configuration;
- `renode/run_openocd_e2e.py`: launches Renode, the bridge, and compiled
  OpenOCD, then executes standard flash and debug commands.

The full harness uses:

```text
flash info 0
flash erase_sector 0 0 last
flash write_image firmware.hex
verify_image firmware.hex
```

It then checks PC access, step, program-memory reads/writes, hardware
breakpoints, all watchpoint modes, asynchronous resume/halt, reset, and a final
verification pass.

## Validation performed

- `python -m pytest -q`: **211 passed**.
- Stateful Renode-compatible GDB RSP tests: connect, feature discovery,
  asynchronous continue/interrupt, halt, single-step, PC access, chunked memory
  access, erase, Intel HEX programming, verification/mismatch reporting,
  breakpoints, all three watchpoint modes, and reset.
- OpenOCD Tcl parsing through `tclsh` for generic hardware, PIC16 Renode, PIC18
  Renode, dsPIC30F5011 Renode, and dsPIC33 Renode configurations.
- dsPIC30F5011 logical-to-sysbus image relocation, already-rebased image
  handling, flash erase/program/verify, and matching platform geometry.
- OpenOCD installer tests for target/flash copying, current and legacy Automake
  paths, target and flash driver registration, removal, dry-run behavior, and
  idempotency.
- Static callback tests for the registered NOR driver and tests that the E2E
  harness uses standard OpenOCD flash commands.
- Python syntax compilation for the changed launch and installer scripts.

## Not performed in this environment

- **Actual Renode executable run:** the environment has no .NET/Mono runtime and
  no prebuilt custom-cores Renode binary. The full protocol was exercised with
  a stateful Renode-compatible GDB server; the three-process harness is ready
  to run against the user's built branch.
- **Exact OpenOCD compilation/run:** network/DNS restrictions prevented cloning
  and compiling the current `xsession/openocd` checkout here. Installer anchors
  and source structure were checked against its current layout, but a native C
  build is still required on the target development machine.
- **Physical PICkit 4 qualification:** electrical ICSP behavior, device-pack
  address units, programming-mode transitions, row alignment, configuration
  memory, erase mode, and recovery after tool/USB failure still require real
  hardware testing.
- **Complete CPU register model:** the OpenOCD target currently exposes PC as
  the minimal GDB register cache. Core execution and breakpoint testing work
  through the backend, but production source-level debugging may require full
  per-core register descriptions from the custom Renode implementations.

## Qualification command

```bash
python renode/run_openocd_e2e.py \
  --renode /path/to/xsession-renode/renode \
  --openocd /path/to/xsession-openocd/src/openocd \
  --core pic18 \
  --firmware /path/to/test.hex
```

Run the same command with `--core pic16`, `--core dspic30`, and
`--core dspic33`, then archive the four generated Renode/bridge/OpenOCD log
sets with the exact commit IDs.
