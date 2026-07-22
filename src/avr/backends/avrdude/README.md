# AVR Backend Source Import

This directory contains the imported AVRDUDE `libavrdude` backend source used
as the basis for native OpenOCD AVR programming backends.

Source:

- Repository: `https://github.com/avrdudes/avrdude.git`
- Commit: `7154723b9efa8bad989b2b339c303aa9d12014e2`
- Primary catalog: `avrdude.conf.in`

Current OpenOCD integration state:

- The MCU and programmer catalogs are generated into `src/avr/avr_catalog_data.c`
  and exposed through native OpenOCD `mcu` and `programmer` commands.
- The complete AVRDUDE backend source is imported here for porting.
- The backend source is not linked directly into OpenOCD yet. It still expects
  AVRDUDE build-system outputs such as `config_gram.c`, `config_gram.h`,
  `lexer.c`, and AVRDUDE-specific feature configuration.

Porting order:

1. Add an OpenOCD AVR backend compatibility header that replaces AVRDUDE's
   generated `ac_cfg.h` with OpenOCD configure results.
2. Generate or vendor the parser outputs required by `config.c`, or replace the
   parser with OpenOCD's generated `src/avr/avr_catalog_data.c` data path.
3. Compile backend families as OpenOCD modules in small groups:
   `stk500`, `stk500v2`, `serialupdi`, `usbasp`, `usbtiny`, `jtagice`,
   `debugwire`, `avrftdi`, `linuxgpio`, and `linuxspi`.
4. Route backend logging through OpenOCD's `LOG_*` APIs.
5. Replace AVRDUDE process-level assumptions with OpenOCD command contexts,
   target lifecycle, and packaging rules.

Do not expose a backend as integrated until it builds with OpenOCD and has at
least one dry-run or hardware validation path.
