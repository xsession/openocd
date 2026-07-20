# Renode custom-cores integration

This directory tests the generated SVDs with the experimental dsPIC support in
`xsession/renode`, branch `custom-cores`.

## What is compatible

The SVD files describe byte-addressed dsPIC data-space SFRs. Renode's current
`dspic30f5011.repl` and dsPIC33F platform files also map SFR peripherals at byte
addresses, so Cortex-Debug can read the same addresses through Renode's GDB
server.

The SVD is consumed by Cortex-Debug, not by the CPU translator. It therefore
cannot add missing instructions, interrupts, or peripheral behavior to Renode.

## Current branch status

| Device | Exact branch platform | Status |
|---|---|---|
| dsPIC30F5011 | `dspic30f5011.repl` | Static integration available |
| dsPIC33FJ128MC802 | none | `dspic33fj128gm802.repl` is only a near match |
| dsPIC33FJ128MC804 | none | exact `.repl` required |
| dsPIC33EP128GM604 | none | exact `.repl` required |

The custom core exposes a dsPIC33 GDB architecture and a W0-W15/PC/status
register map. Its target-description feature list and interrupt selection are
still incomplete, so passing the static check is not a claim of production
firmware compatibility.

## Static validation

```bash
python scripts/validate_renode.py \
  --renode-root ../renode \
  --svd-dir svd \
  --json metadata/renode-compatibility.json
```

The command checks:

- `dspic33.le` is included in `build.sh`;
- the dsPIC33 CPU and GDB architecture declarations exist;
- the essential GDB register mapping exists;
- exact platform files are present for each requested part;
- generated SVD register addresses can be compared with mapped `.repl` ranges.

Use `--strict` in CI after all four exact platforms and the GDB target
implementation are complete.

## Runtime smoke test: dsPIC30F5011

Build the custom branch and start the supplied script from the Renode checkout:

```bash
./build.sh --no-gui
./renode --console --disable-gui \
  -e '$bin=@/absolute/path/to/firmware.elf' \
  -e 'include @/absolute/path/to/dspic-svd/renode/dspic30f5011.resc'
```

Then use `renode/cortex-debug-renode.launch.jsonc` as the basis for `.vscode/launch.json`.
The GDB executable must understand Renode's `dspic33` target architecture.

A meaningful runtime test must confirm all of the following:

1. Renode loads the ELF and reaches the reset PC.
2. The GDB client reads W0-W15, PC, STATUS and stack state.
3. Cortex-Debug can read a known SFR through `svdFile`.
4. A breakpoint at `main` is hit.
5. Single-step and continue work without a translator exception.
6. At least one modeled peripheral register changes as firmware executes.
