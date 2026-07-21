# TI C2000 XDS100 Examples

This folder contains TI C2000 example configs that pair one C2000 target family
with either an XDS100v2 or XDS100v3 probe.

Run examples from the repository root:

```console
openocd -s ./tcl -f examples/c2000/<file>.cfg
```

## Available Examples

| File | Target | Probe |
| --- | --- | --- |
| `tms320f280049-xds100v2.cfg` | TMS320F280049 | XDS100v2 |
| `tms320f280049-xds100v3.cfg` | TMS320F280049 | XDS100v3 |
| `tms320f28069-xds100v2.cfg` | TMS320F28069 | XDS100v2 |
| `tms320f28069-xds100v3.cfg` | TMS320F28069 | XDS100v3 |
| `tms320f28m35x-xds100v2.cfg` | TMS320F28M35x Concerto | XDS100v2 |
| `tms320f28m35x-xds100v3.cfg` | TMS320F28M35x Concerto | XDS100v3 |

## Safe Discovery Command

Use this first:

```console
openocd -s ./tcl -f examples/c2000/tms320f28m35x-xds100v3.cfg -c "init; scan_chain; shutdown"
```

For C2000 ICEPick-based targets, useful follow-up commands may include:

```console
openocd -s ./tcl -f examples/c2000/tms320f28m35x-xds100v3.cfg \
  -c "init; scan_chain; c2000_icepick_read_idcode; c2000_icepick_scan_sdtaps; shutdown"
```

## Debug Session

After discovery works, start OpenOCD without `shutdown`:

```console
openocd -s ./tcl -f examples/c2000/tms320f28069-xds100v3.cfg
```

Flash commands are intentionally omitted from these C2000 examples until erase,
write, verify, protection, and recovery behavior are verified on real hardware.

## Troubleshooting

- If the probe is not found, check USB driver binding and probe serial
  selection.
- If `scan_chain` fails, check target power, JTAG wiring, TRST, and adapter
  speed.
- If ICEPick commands work but CPU debug does not, the router is visible but
  the CPU debug transport still needs target-specific support.
- Start at `adapter speed 100` or `adapter speed 500` when testing new boards.
