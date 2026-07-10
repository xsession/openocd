# OpenOCD binary package deployment with Docker

This project uses Docker only for reproducible binary package builds. It does
not use Docker Compose to run OpenOCD against USB/JTAG hardware.

## Output layout

Packages are written under:

```text
docker/data/dist/linux/amd64/openocd-linux-x86_64.tar.gz
docker/data/dist/linux/arm64/openocd-linux-aarch64.tar.gz
docker/data/dist/windows/openocd-windows-x86_64.zip
docker/data/dist/macos/openocd-macos-x86_64.tar.gz
docker/data/dist/macos/openocd-macos-arm64.tar.gz
```

## Recommended commands

Build and export the default Docker-supported packages with Compose:

```sh
docker compose up --build
```

Default Compose builds `linux/amd64` and `windows/x86_64`. It intentionally skips `linux/arm64` on Windows/amd64 hosts because ARM64 containers need QEMU/binfmt emulation.

Build ARM64 too after enabling emulation:

```sh
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker compose --profile arm64 up --build
```

`docker compose build` is also valid, but it only builds the package images.
The artifacts are copied to `docker/data/dist` when the containers run, so use
`docker compose up --build` for a full package export.

Build and export the default Buildx Bake targets:

```sh
docker buildx bake
```

Build every Docker-supported target, including linux/arm64:

```sh
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker buildx bake all
```

Build Linux amd64 package only:

```sh
scripts/build-linux-package.sh
```

Build Linux amd64 + arm64 after enabling emulation:

```sh
BUILD_ARM64=1 scripts/build-linux-package.sh
```

Build Windows package only:

```sh
scripts/build-windows-cross.sh
```

Build macOS packages on macOS:

```sh
scripts/build-macos-package.sh
```

## Why Compose has no `outputs:` key

`outputs:` is a Buildx/Bake feature, not a Docker Compose build property. The
Compose file therefore builds Dockerfile target `package`, mounts `/dist`, and
runs a tiny copy command that transfers `/out` from the image into the mounted
host output directory.

For direct local export using `--output type=local`, use `docker buildx bake` or
the scripts in `scripts/`.


### Windows checkout bootstrap fix

If Docker logs show `./bootstrap: not found` even though `bootstrap` exists, the packaging Dockerfiles normalize CRLF and execute it through `sh ./bootstrap`. No Git line-ending configuration change is required for this packaging flow.


### Windows line-ending note

The Docker packaging images normalize Autotools files to LF before running `bootstrap`. This is required for Windows checkouts where CRLF line endings can make `aclocal`/`autom4te` fail even though the source tree looks correct.

### Source archives without submodules

If your OpenOCD checkout/archive does not contain `jimtcl/autogen.sh`, the Docker packaging build now fetches the missing Jim Tcl submodule automatically before running `bootstrap`. This is useful for ZIP exports or copied source trees that do not include Git submodules.


### Windows checkout line endings

If building from a Windows checkout, the Dockerfiles normalize Autotools files, `bootstrap`, `autogen.sh`, and `*.sh` files to LF and restore executable bits before running bootstrap. This avoids failures such as `./bootstrap: not found` or `./autogen.sh: not found` caused by CRLF shebangs inside the Linux build container.


### libconfuse / ftdi_eeprom note

For the Windows package, libconfuse is still built so libftdi can include `ftdi_eeprom`. The Dockerfile intentionally builds only libconfuse's library subtree, because the upstream example binaries are not required and some do not cross-compile cleanly with MinGW.

### libjaylink fetch fallback

The Windows cross-build fetches libjaylink through a fallback chain because repo.or.cz snapshot downloads can fail with TLS EOF errors in Docker builds. The builder first tries the upstream GitLab repository, then a GitHub mirror, then repo.or.cz with curl retries.
