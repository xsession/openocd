# Source map for contributors

Use this page to find the smallest correct change surface. Prefer changing the
highest-level layer that expresses the behavior; do not duplicate a board or
probe decision in C when a Tcl configuration or support metadata entry is the
appropriate source of truth.

## Runtime source map

| Question | Start here | Then inspect |
|---|---|---|
| How does the executable start and stop? | `src/main.c`, `src/openocd.c` | `src/server/server.c`, `src/helper/command.c` |
| How are CLI flags and `-f` files handled? | `src/helper/options.c` | `src/helper/configuration.c`, `src/openocd.c` |
| How are commands registered? | `src/helper/command.h`, `src/helper/command.c` | `struct command_registration` tables and `command_registrants[]` |
| How are scripts found? | `src/helper/options.c` | `OPENOCD_SCRIPTS`, user directories, package data, `Makefile.am` install hook |
| How does GDB connect? | `src/server/gdb_server.c` | `src/target/target.c`, `src/flash/nor/core.c` |
| How do Telnet/Tcl clients connect? | `src/server/telnet_server.c`, `src/server/tcl_server.c` | `src/server/server.c`, command context |
| How is a probe selected? | `src/jtag/interfaces.c`, `src/jtag/adapter.c` | `src/jtag/drivers/`, `tcl/interface/` |
| How is JTAG/SWD/SWIM selected? | `src/transport/transport.c` | `src/target/adi_v5_*`, `src/jtag/`, interface Tcl |
| How is a CPU modeled? | `src/target/target.c`, `src/target/target_type.h` | architecture/target implementation and `tcl/target/` |
| How does memory access work? | `src/target/target.c`, `src/target/target.h` | target-specific callbacks, algorithms, and transport/DAP code |
| How does flash programming work? | `src/flash/nor/core.c`, `src/flash/nor/driver.h` | selected `src/flash/nor/*.c`, `tcl/target/` flash bank commands |
| How are FPGA/CPLD images handled? | `src/pld/`, `src/svf/`, `src/xsvf/` | `tcl/fpga/`, `tcl/cpld/`, `pld`/`svf` commands |
| How does AVR programming work? | `src/avr/` | embedded AVRDUDE backend, `tcl/programmer/avrdude/`, catalog data |
| How does Microchip RI4/PICkit support work? | `src/programmer/microchip/`, `src/target/mchp_ri4_*` | `tcl/programmer/microchip/`, interface configs, tests, examples |
| How are RTOS and RTT features added? | `src/rtos/`, `src/rtt/` | target hooks, server service registration, Tcl commands |

## Runtime data map

| Directory | Contract |
|---|---|
| `tcl/interface/` | Selects and configures a physical adapter/probe. |
| `tcl/target/` | Defines an MCU/SoC debug chain, reset, memory, and flash banks. |
| `tcl/board/` | Combines a physical board with interface and target definitions. |
| `tcl/programmer/` | Adds programmer-specific command and delegation flows. |
| `tcl/chip/`, `tcl/cpu/`, `tcl/packs/` | Reusable chip, CPU, and generated/package-derived definitions. |
| `tcl/fpga/`, `tcl/cpld/` | FPGA/CPLD programming configuration. |
| `support/` | Curated metadata, catalogs, vendors, board/programmer records, and validation helpers. |
| `svd/` | Committed debugger register descriptions; generator sources live under `tools/`. |
| `examples/` and `samples/` | User-facing configurations and IDE integrations; keep examples runnable and clearly scoped. |
| `udev/` and `contrib/` | Host permissions and upstream-style auxiliary integration assets. |

## Build and delivery map

| Change | Files that usually need review |
|---|---|
| Add an adapter | `configure.ac`, adapter header, `src/jtag/drivers/`, `src/jtag/interfaces.c`, `src/jtag/drivers/Makefile.am`, interface Tcl, docs, tests |
| Add a target family | `src/target/`, target registry, target Makefile, `tcl/target/`, board examples, support matrix |
| Add a flash chip | `src/flash/nor/`, flash driver registry, target Tcl, erase/write/verify tests |
| Add a board | `tcl/board/`, target/interface references, optional `support/boards/` metadata, example and user docs |
| Add a programmer bridge | native bridge source or `tools/debug-servers/`, `tcl/programmer/`, workflow tests, external-runtime docs |
| Change installed scripts | `tcl/`, `Makefile.am`, package Dockerfiles, path/search documentation |
| Change packaging | `docker/`, `.github/workflows/`, `README.md`, deployment docs, artifact smoke tests |
| Change the documentation site | `mkdocs.yml`, `docs/`, `docs/requirements.txt`, docs workflow, generated pages |

## Review rule

Every source change should answer three questions:

1. Which runtime container owns the behavior?
2. Is the behavior reusable across boards, or should it remain in Tcl/support
   data?
3. Which build, package, workflow, hardware, and documentation paths exercise
   it?

The answer belongs in the change description and, for cross-cutting changes,
in [Architecture decisions](decisions.md).
