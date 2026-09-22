# C4 components: source-level responsibilities and call flow

This view goes one level below the logical containers. It is intentionally
organized around stable source responsibilities rather than individual vendor
drivers.

```mermaid
C4Component
  title Main OpenOCD runtime components

  Container_Boundary(runtime, "OpenOCD runtime") {
    Component(entry, "Entry and lifecycle", "src/main.c, src/openocd.c", "Starts the process, registers commands, runs init, and performs cleanup")
    Component(commands, "Command registry", "src/helper/command.c", "Owns command contexts, dispatch, Tcl evaluation, and command modes")
    Component(config, "Options and script discovery", "src/helper/options.c, configuration.c", "Resolves CLI files, search paths, installed scripts, and user overrides")
    Component(services, "Service/event loop", "src/server/server.c", "Accepts connections and dispatches GDB, Telnet, Tcl, and target events")
    Component(link, "Adapter and transport", "src/jtag/, src/transport/", "Selects JTAG/SWD/SWIM/DAP paths and drives adapter implementations")
    Component(target, "Target model", "src/target/", "Creates target types and performs examine, reset, halt, resume, memory, and register operations")
    Component(program, "Programming engines", "src/flash/, src/programmer/, src/avr/, src/pld/", "Maps image/programming commands to flash, AVR, Microchip, FPGA, and CPLD operations")
    Component(runtime_data, "Runtime configuration", "tcl/, svd/, support/, udev/", "Selects concrete board, probe, target, programmer, and debugger data")
  }

  Rel(entry, commands, "creates and registers")
  Rel(entry, config, "runs after command-line parsing")
  Rel(commands, config, "evaluates script commands")
  Rel(services, commands, "uses shared command context")
  Rel(services, target, "forwards debugger operations and events")
  Rel(link, target, "provides transport/debug-port access")
  Rel(target, program, "provides memory and execution primitives")
  Rel(program, link, "uses target and adapter paths")
  Rel(runtime_data, config, "loaded by search path")
  Rel(runtime_data, link, "configures adapter and transport")
  Rel(runtime_data, target, "creates target/board definitions")
```

## Startup and initialization flow

```mermaid
sequenceDiagram
  participant Main as src/main.c
  participant Runtime as src/openocd.c
  participant Cmd as command context
  participant Config as Tcl/configuration
  participant Server as server services
  participant Core as target/adapter/flash core

  Main->>Runtime: openocd_main(argc, argv)
  Runtime->>Cmd: command_init(embedded startup Tcl)
  Runtime->>Cmd: register subsystem command groups
  Runtime->>Config: parse_cmdline_args and parse_config_file
  Runtime->>Server: server_preinit and server_init
  Runtime->>Cmd: run init
  Cmd->>Core: target init
  Cmd->>Core: adapter init
  Cmd->>Core: transport init
  Cmd->>Core: dap init and target examine
  Cmd->>Core: flash/nand/pld/tpiu init
  Core-->>Server: register GDB services for available targets
  Server-->>Runtime: server_loop until shutdown
```

The ordering is significant. Configuration must select the adapter and target
before `init`; target examination must happen before GDB services are attached;
and flash/PLD initialization is performed after the target/debug path is ready.
The implementation is visible in `handle_init_command()` and
`openocd_thread()` in `src/openocd.c`.

## Operation flow: GDB flash programming

```mermaid
sequenceDiagram
  participant GDB as GDB / IDE
  participant Server as gdb_server.c
  participant Target as target.c
  participant Flash as flash/nor/core.c
  participant Driver as selected flash driver
  participant Probe as adapter driver

  GDB->>Server: Remote Serial Protocol memory/flash request
  Server->>Target: halt, read memory, or invoke image operation
  Target->>Flash: select configured flash bank
  Flash->>Driver: erase/write/verify callback
  Driver->>Target: target memory or algorithm access
  Target->>Probe: transport transaction
  Probe-->>Target: device response
  Target-->>Flash: result and status
  Flash-->>Server: success or error
  Server-->>GDB: RSP response
```

## Extension points

| Extension kind | Interface/registry | Typical files | Runtime selection |
|---|---|---|---|
| Adapter | `struct adapter_driver`, `adapter_drivers[]` | `src/jtag/drivers/*.c`, `src/jtag/interfaces.c` | `tcl/interface/*.cfg` and configure flags |
| Transport | `struct transport`, `transport_register()` | `src/transport/`, `src/target/adi_v5_*` | `transport select`, adapter capabilities, and Tcl |
| Target | `struct target_type`, `target_types[]` | `src/target/*.c` | `tcl/target/*.cfg` |
| NOR flash | `struct flash_driver` | `src/flash/nor/*.c` | `flash bank` command in Tcl |
| NAND controller | controller registry | `src/flash/nand/` | NAND Tcl commands |
| Programmer | command registrants and Tcl bridge | `src/programmer/`, `src/avr/`, `tcl/programmer/` | programmer/board config |
| PLD/SVF/XSVF | PLD driver tables and command groups | `src/pld/`, `src/svf/`, `src/xsvf/` | `pld`, `svf`, or `xsvf` commands |
| RTOS/trace | target hooks and service registrants | `src/rtos/`, `src/rtt/`, `src/server/` | target detection and Tcl configuration |

New code should follow the existing registry pattern and keep board-specific
choices in Tcl or support metadata where possible.
