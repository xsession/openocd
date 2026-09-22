# Architecture decisions and stable boundaries

These decisions describe how to extend the project without making the source
tree harder to build, package, or use from embedded-development workflows.

## 1. Keep upstream build-critical paths stable

`src/`, `tcl/`, `contrib/`, `doc/`, `jimtcl/`, and the existing Autotools files
are integration boundaries. Zephyr runners, package scripts, installed paths,
and downstream users depend on them. Organize new project material around
those paths instead of moving them for cosmetic reasons.

## 2. Put policy in Tcl/data and mechanics in C

Board composition, adapter IDs, reset policy, target selection, flash-bank
declarations, and user-overridable defaults belong in `tcl/`, `support/`, or
`examples/` when they can be expressed there. C belongs in `src/` when the
behavior is a reusable protocol, architecture, driver, or performance-critical
operation.

This keeps one adapter or target implementation reusable across many boards and
prevents a board-specific workaround from becoming a global default.

## 3. Use registries as explicit extension points

OpenOCD uses static registries for commands, adapters, transports, target
types, flash drivers, and PLD drivers. A new implementation is incomplete until
it is declared, compiled, registered, configured, documented, and tested.

The [new-vendor guide](../development/adding-new-vendor-mcu-programmer.md)
and [extension table](components.md#extension-points) are the practical
checklist.

## 4. Embed only the bootstrap, install the rest as data

Subsystem startup Tcl is embedded into the binary for a version-matched minimum
runtime. Board, interface, target, programmer, and site scripts remain external
package data so they can be overridden, inspected, and packaged independently.

The consequence is deliberate: a working binary without its matching scripts
is not a complete deployment.

## 5. Keep protocol services above hardware drivers

GDB, Telnet, and Tcl clients should not know whether the target is driven by
JTAG, SWD, SWIM, a vendor bridge, or a remote adapter. Protocol code calls
target/session APIs; the session selects a transport and adapter. This is the
main portability boundary of the runtime.

## 6. Treat Docker as a reproducibility boundary

Dockerfiles should orchestrate the native Autotools build and package the
result. They should not create a parallel source layout or silently apply
unreviewed source transformations. Dependency commits, platform flags, USB
access, and artifact paths belong in the Docker/deployment documentation.

## 7. Keep specialist manuals separate

The MkDocs site is the task-oriented navigation and architecture layer. The
Texinfo manual remains the complete OpenOCD command reference, while Doxygen
remains the C API/source reference. Link between these systems instead of
copying their large bodies of content.

## 8. Document hardware-dependent claims honestly

A compile check proves registration and linkage; a config parse proves Tcl
syntax; neither proves that a real probe, cable, reset line, target ID, or flash
algorithm works. Hardware validation must identify the adapter, target, wiring,
transport, expected ID, and operation tested.

This distinction is especially important for the TI C2000/XDS, MSPM0, and
Microchip programmer integrations maintained in this fork.
