# Configuration files

OpenOCD searches its installed script directory and every path supplied with `-s`.

Typical command structure:

```console
$ openocd \
  -f interface/stlink.cfg \
  -c "transport select hla_swd" \
  -f target/stm32f4x.cfg
```

Configuration categories:

- `interface/`: debug adapter drivers and USB identifiers.
- `target/`: CPU, debug, and flash setup.
- `board/`: a known board combining adapter and target settings.
- `cpld/`, `fpga/`, `memory/`: device-specific helpers.

Prefer an existing board file when it exactly matches the hardware. Otherwise compose interface and target files explicitly and keep project-specific settings in a small repository-local `.cfg` file.
