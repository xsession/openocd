# Docker deploy system for `xsession/openocd`

This folder is intended to be copied into the root of `https://github.com/xsession/openocd` as `deploy/` plus the root helper files shown below.

It gives you:

- reproducible Docker build from the OpenOCD source tree;
- optional remote build from `https://github.com/xsession/openocd.git`;
- small runtime image with OpenOCD, scripts, GDB, and USB helpers;
- Docker Compose service exposing GDB/Telnet/Tcl ports;
- host udev rules for common JTAG/SWD probes;
- GitHub Actions workflow for GHCR multi-arch image publishing.

## Microchip PICkit and ICD programming

This fork includes OpenOCD programmer presets for PICkit 2, PICkit 3,
PICkit 4 and MPLAB ICD 4. PIC/dsPIC ICSP operations are exposed as
`microchip` commands and use `pk2cmd` or MPLAB IPECMD as the device-script
backend. PICkit 4 and ICD 4 also have direct CMSIS-DAP interface presets for
compatible JTAG/SWD target modes.

See [`docs/programmers/microchip-pickit-icd.md`](docs/programmers/microchip-pickit-icd.md).

## Install into the repo

```bash
git clone --recursive https://github.com/xsession/openocd.git
cd openocd
mkdir -p deploy
cp -a /path/to/openocd-docker-deploy/docker deploy/
cp -a /path/to/openocd-docker-deploy/scripts deploy/
cp -a /path/to/openocd-docker-deploy/examples deploy/
cp -a /path/to/openocd-docker-deploy/config deploy/
cp -a /path/to/openocd-docker-deploy/udev deploy/
cp /path/to/openocd-docker-deploy/Makefile .
cp /path/to/openocd-docker-deploy/.dockerignore .
cp /path/to/openocd-docker-deploy/docker-bake.hcl .
mkdir -p .github/workflows
cp /path/to/openocd-docker-deploy/.github/workflows/docker.yml .github/workflows/docker.yml
```

## Build local source tree

```bash
make build
make version
```

Equivalent raw Docker command:

```bash
docker build -f deploy/docker/Dockerfile -t xsession/openocd:local .
```

## Build directly from GitHub

Use this when you do not want the repository checkout as Docker context:

```bash
docker build -f deploy/docker/Dockerfile.remote \
  --build-arg OPENOCD_REPO=https://github.com/xsession/openocd.git \
  --build-arg OPENOCD_REF=master \
  -t xsession/openocd:master .
```

For your `custom-cores` branch:

```bash
make build-remote REMOTE_REF=custom-cores IMAGE=xsession/openocd:custom-cores
```

## Run with a probe attached

Linux host:

```bash
sudo cp deploy/udev/99-openocd-probes.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then run:

```bash
make run CONFIG=examples/stlink-stm32f4.cfg
```

Or directly:

```bash
docker run --rm -it --privileged \
  --device=/dev/bus/usb:/dev/bus/usb \
  -p 3333:3333 -p 4444:4444 -p 6666:6666 \
  -v "$PWD/examples:/work/examples:ro" \
  xsession/openocd:local \
  -f examples/stlink-stm32f4.cfg
```

Connect GDB from the host:

```bash
arm-none-eabi-gdb firmware.elf
(gdb) target extended-remote localhost:3333
```

## Docker Compose service

Edit `deploy/config/default.cfg` or override `command:` in `deploy/docker-compose.yml`, then:

```bash
make compose-up
```

OpenOCD ports:

- `3333`: GDB server
- `4444`: Telnet command console
- `6666`: Tcl RPC

## Security notes

The Compose file uses `privileged: true` because many USB probes need raw USB access and hotplug behavior. For a locked-down deployment, replace it with only the exact devices and groups you need, for example:

```yaml
devices:
  - /dev/bus/usb/001/005:/dev/bus/usb/001/005
group_add:
  - plugdev
```

Also keep `OPENOCD_BINDTO=127.0.0.1` unless you intentionally expose the debugger on the LAN.

## Windows and WSL2 notes

Docker Desktop on Windows does not pass arbitrary USB devices to Linux containers the same way a Linux host does. Use one of these options:

1. Run the container on a real Linux machine close to the target hardware.
2. Use WSL2 plus `usbipd-win` to attach the probe to WSL, then run Docker inside that WSL environment.
3. Run OpenOCD natively on Windows and use the Docker image only in CI/build environments.

## Custom configure flags

Set `CONFIGURE_FLAGS` at build time:

```bash
make build CONFIGURE_FLAGS='--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-jimtcl'
```

For unusual probes, check `./configure --help` inside the repo and enable the adapter explicitly.

## Recommended repo layout after install

```text
openocd/
  deploy/
    docker/Dockerfile
    docker/Dockerfile.remote
    docker-compose.yml
    scripts/openocd-entrypoint.sh
    config/default.cfg
    examples/*.cfg
    udev/99-openocd-probes.rules
  .github/workflows/docker.yml
  .dockerignore
  docker-bake.hcl
  Makefile
```
