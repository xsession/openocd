# Legacy command manual

The authoritative OpenOCD command reference remains `doc/openocd.texi`. It covers server commands, adapters, transports, targets, flash drivers, boundary scan, Tcl, and GDB integration.

Build the Info/manual outputs through the normal Autotools build. The Sphinx deployment guide deliberately does not duplicate this content.

For source developers, `Doxyfile.in` generates API documentation from C sources. A future Sphinx integration can consume Doxygen XML through Breathe while keeping the upstream build unchanged.
