# dsPIC SVD for Cortex-Debug

Reproducible CMSIS-SVD generation for selected Microchip dsPIC Digital Signal Controllers, with explicit compatibility checks for the VS Code Cortex-Debug peripheral viewer.

## Supported devices

| Device | Family pack | Pinned version |
|---|---|---:|
| dsPIC30F5011 | `Microchip.dsPIC30F_DFP` | `1.6.395` |
| dsPIC33FJ128MC802 | `Microchip.dsPIC33F-GP-MC_DFP` | `1.5.373` |
| dsPIC33FJ128MC804 | `Microchip.dsPIC33F-GP-MC_DFP` | `1.5.373` |
| dsPIC33EP128GM604 | `Microchip.dsPIC33E-GM-GP-MC-GU-MU_DFP` | `1.7.401` |

The source register descriptions are extracted from pinned Microchip Device Family Pack (`.atpack`) files. The converter supports both ATDF and the EDC `.PIC` XML format used by many 16-bit Microchip packs.

> Vendor-derived SVD files are not committed to the source archive. Run `make update` on a networked machine, or run the **Refresh generated SVDs** GitHub Actions workflow, to generate the four SVDs and associated artifacts.

## Cortex-Debug usage

For the peripheral register view, point Cortex-Debug directly at the generated file:

```jsonc
{
  "name": "dsPIC33EP128GM604: external GDB server",
  "type": "cortex-debug",
  "request": "attach",
  "servertype": "external",
  "gdbTarget": "localhost:3333",
  "gdbPath": "C:/path/to/dspic-capable-gdb.exe",
  "objdumpPath": "C:/path/to/xc16-objdump.exe",
  "toolchainPrefix": "xc16",
  "executable": "${workspaceFolder}/firmware.elf",
  "device": "dsPIC33EP128GM604",
  "svdFile": "${workspaceFolder}/svd/dspic33ep128gm604.svd"
}
```

A complete template is in `examples/vscode/cortex-debug-external.launch.jsonc`.

## Renode custom-cores integration

The repository includes a static compatibility checker and a Cortex-Debug/Renode
smoke-test setup for `xsession/renode`, branch `custom-cores`:

```bash
make renode-check RENODE_ROOT=../renode
```

The checked branch currently builds an experimental `dspic33.le` translator and
contains an exact `dspic30f5011.repl`. It does not yet contain exact platform
descriptions for `dsPIC33FJ128MC802`, `dsPIC33FJ128MC804`, or
`dsPIC33EP128GM604`. The similarly named `dspic33fj128gm802.repl` is not treated
as an MC802 replacement.

See `renode/README.md` for the compatibility matrix, runtime smoke script,
Cortex-Debug launch configuration, and the limitations of the current interrupt
and GDB target-description implementation.

The SVD controls only peripheral presentation and memory addresses. Cortex-Debug still needs a dsPIC-capable GDB executable and an external GDB remote server that can control the target. If your probe/debugger is exposed only through another VS Code debug adapter, use the standalone MCU Peripheral Viewer and configure its `svdPath`; see `examples/vscode/other-debugger.launch.jsonc`.

## What the compatibility validator guarantees

`make cortex-debug-check` verifies the exact XML shape expected by Cortex-Debug's peripheral parser, including:

- one concrete `peripherals` container and register array;
- byte-addressed `baseAddress` and `addressOffset` values (`addressUnitBits = 8`);
- supported access strings and integer encodings;
- non-overlapping register and field ranges;
- register sizes, reset values, enum widths, and address-block coverage;
- stable names, `displayName`, `groupName`, and enum group names.

Generated files intentionally omit the optional Arm-specific `<cpu>` element. The dsPIC SFR space is represented as one `SFR` peripheral at base address `0`, with each SFR's real data-space address stored as its byte `addressOffset`.

## Build and validate

Requirements: Python 3.11+ and GNU Make.

```bash
python -m venv .venv
. .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
make update
make check-generated
make html
make mmaps
make support-pack
```

Generated files are written to:

- `sources/`: extracted Microchip source descriptors
- `svd/`: generated and patched CMSIS-SVD files
- `metadata/`: provenance, hashes, and compatibility status
- `mmaps/`: compact text memory maps
- `html/`: browsable register maps
- `vscode-support/data/`: validated SVDs ready for the optional support-pack extension

## Commands

```bash
make update               # download pinned packs, extract descriptors, generate and patch SVDs
make generate             # regenerate from already extracted source descriptors
make patch                # apply reviewed device YAML corrections and revalidate
make lint                 # generic structural SVD validation
make cortex-debug-check   # validate Cortex-Debug peripheral-viewer compatibility
make test                 # unit tests, including a generated-SVD parser compatibility test
make check                # tests + structural validation (works before vendor files exist)
make check-generated      # tests + both validators; use after make update
make html                 # browsable HTML register maps
make mmaps                # compact memory maps
make support-pack         # copy validated SVDs into the VS Code support-pack scaffold
make renode-check RENODE_ROOT=../renode  # inspect custom-cores compatibility
make vsix                 # build the optional VSIX through @vscode/vsce
make clean                # remove generated outputs
```

For manually downloaded packs:

```bash
python scripts/update_packs.py \
  --pack-file Microchip.dsPIC30F_DFP.1.6.395.atpack \
  --pack-file Microchip.dsPIC33F-GP-MC_DFP.1.5.373.atpack \
  --pack-file Microchip.dsPIC33E-GM-GP-MC-GU-MU_DFP.1.7.401.atpack
```

## Repository design

The generation path is deterministic:

1. download a pinned Microchip pack;
2. locate the exact `.PIC` or `.atdf` descriptor;
3. parse SFRs, fields, enumerations, aliases, and interrupts;
4. write a conservative CMSIS-SVD subset;
5. apply reviewed YAML corrections;
6. run generic and Cortex-Debug-specific validators;
7. record source hashes, output hashes, pack version, and compatibility status.

The scripts and original project files are Apache-2.0 licensed. Microchip pack contents remain subject to Microchip's licenses and are not relicensed by this project.
