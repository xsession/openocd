# Test organization

The test tree is split by execution model:

- `tcl_commands/`: Tcl command and configuration regression tests.
- `microchip_programmer/`: Python tests for the Microchip programmer bridge
  and its generated Tcl commands.
- `examples/`: legacy compiled example programs and historical test fixtures.
- Root-level Tcl/HTML files: the upstream OpenOCD test harness and smoke-test
  entry points.

Run the focused Microchip tests directly from the repository root:

```console
python3 testing/microchip_programmer/test_microchip_programmer.py
```

The normal Autotools test entry point remains `make check`; keep new tests
close to the subsystem they exercise and register them in the nearest
`Makefile.am` when they require build-system integration.
