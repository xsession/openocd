# AVRDUDE Catalog

This directory contains generated OpenOCD support metadata derived from an
AVRDUDE `avrdude.conf` catalog.

Generated files:

- `parts.yml`: AVRDUDE part IDs, aliases, descriptions, signatures,
  programming interfaces, and memory names.
- `programmers.yml`: AVRDUDE programmer IDs, aliases, descriptions, transport
  types, connection types, and USB identifiers when present.

Regenerate the catalog with:

```powershell
powershell -ExecutionPolicy Bypass -File tools\support\generate-avrdude-catalog.ps1 -Config path\to\avrdude.conf
```

If `-Config` is omitted, the generator checks `AVRDUDE_CONF`, an installed
`avrdude` executable, and `artifacts/vendor-sources/avrdude/src/avrdude.conf.in`.

The generator also emits `src/avrdude/avrdude_catalog_data.c`, which is
compiled into OpenOCD and exposed through the native `avrdude_catalog` command.
Runtime AVR programming remains delegated through
`tcl/programmer/avrdude/common.tcl` until protocol backends are ported.
