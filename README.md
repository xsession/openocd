# xsession OpenOCD unified fork

**Unified release:** `2026.07.17`

This repository is a single coherent OpenOCD source tree containing the
cross-platform deployment work and the additional target, adapter, and
programmer support developed for the `xsession/openocd` fork.

## Included feature sets

### Texas Instruments

- TMS320/C2000 target-family definitions, generated device configurations, and
  generic scan helpers.
- C28x target/backend integration carried by the custom fork.
- Device presets for:
  - TMS320F28M35x
  - TMS320F28069
  - TMS320F280049
- XDS100v2 and XDS100v3 FTDI adapter configurations.
- Existing XDS110 support retained.
- MSPM0C1103 target and board configurations, including XDS110 and CMSIS-DAP
  launch paths.

See:

- [`docs/targets/ti-tms320-family-support.md`](docs/targets/ti-tms320-family-support.md)
- [`docs/targets/ti-c2000-support.md`](docs/targets/ti-c2000-support.md)
- [`docs/targets/ti-mspm0c1103.md`](docs/targets/ti-mspm0c1103.md)

### Microchip programmers

OpenOCD Tcl commands and presets are included for:

- PICkit 2 through `pk2cmd`
- PICkit 3 through MPLAB IPECMD or legacy `pk2cmd`
- PICkit 4 through MPLAB IPECMD, with a separate CMSIS-DAP interface preset
- MPLAB ICD 4 through MPLAB IPECMD, with a separate CMSIS-DAP interface preset

The proprietary PIC/dsPIC ICSP algorithms and device databases are not copied
into this repository. The integration invokes an installed programming
backend while presenting one consistent OpenOCD command surface.

See [`docs/programmers/microchip-pickit-icd.md`](docs/programmers/microchip-pickit-icd.md).

### Build and deployment

- Native Linux and macOS build helpers.
- Docker-based Linux packages.
- Docker/MinGW Windows cross-packages.
- Docker Compose runtime support.
- GitHub Actions workflows.
- Udev rules covering the added TI and Microchip probes.
- VS Code and Cortex-Debug examples retained from the custom fork.

See [`docs/index.md`](docs/index.md) for the custom documentation index.

## Clone and bootstrap

```console
git clone --recursive https://github.com/xsession/openocd.git
cd openocd
./bootstrap
./configure --enable-internal-jimtcl --disable-werror
make -j"$(nproc)"
make check
```

Do not use a narrow `--enable-targets=` configuration when the additional
target backends are required.

## Cross-platform package build

The repository-level Docker and script helpers produce Linux and Windows
archives under `artifacts/`.

```console
docker compose -f docker/compose.yaml up --build
```

Or build all configured Docker targets:

```console
docker buildx bake -f docker/docker-bake.hcl all
```

Native macOS packaging is provided by:

```console
./docker/scripts/build-macos-package.sh
```

## Example: TI C2000 with XDS100v2

```console
openocd   -f interface/ftdi/xds100v2.cfg   -f target/ti/tms320f28069.cfg
```

Use `interface/ftdi/xds100v3.cfg` for an XDS100v3 probe.

## Example: PICkit 4 programming a dsPIC

```console
openocd   -f programmer/microchip/pickit4.cfg   -c "microchip device dsPIC33EP128GM604"   -c "microchip executable /opt/microchip/mplabx/mplab_platform/mplab_ipe/ipecmd.sh"   -c "microchip vdd external"   -c "microchip program build/firmware.hex"   -c shutdown
```

The PICkit/ICD presets are programming bridges. Full source-level dsPIC
debugging still requires a dsPIC-capable target backend and GDB server.

## Validation

The unified package is checked for:

- source-tree merge conflicts;
- missing feature files;
- Python tests for all Microchip programmer presets;
- Autotools bootstrap/configuration;
- OpenOCD compilation when the build environment provides all dependencies;
- archive checksums.

See [`MERGE_MANIFEST.md`](MERGE_MANIFEST.md) for the exact merge contents and
validation status.
