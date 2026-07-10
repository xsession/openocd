# Packaging refactor notes

This tree was refactored so Docker is only used to build binary deployment artifacts.

Removed from the Docker workflow:

- Runtime OpenOCD container behavior
- USB/JTAG device passthrough in Compose
- GDB/Telnet/Tcl exposed ports in Compose
- Entrypoint-driven `openocd` service execution

Added/kept for deployment builds:

- Linux package export for amd64 and arm64
- Windows x86_64 cross-build export
- macOS package script for native macOS runners
- GitHub Actions workflow for all three OS families
- Buildx Bake and Compose package-builder definitions
- `JOBS=0` normalization
- `--disable-werror` forced for deploy/package builds
- Windows cross-build dependency chain including libconfuse so `ftdi_eeprom` can remain enabled

## Compose outputs fix

Docker Compose does not accept `build.outputs`. The Compose file now targets the
Dockerfile `package` stages and mounts host output directories at `/dist`.
Use `docker compose up --build` to build and copy artifacts into
`docker/data/dist`. Use `docker buildx bake` when direct Buildx local output is
preferred.

## 2026-07-09 Dockerfile heredoc parser fix

Fixed Dockerfile parser failure:

    target linux-amd64: failed to solve: unterminated heredoc

Cause: `cat <<'EOS'` was embedded inside a backslash-continued `RUN` command. BuildKit's Dockerfile parser treats heredocs specially and requires the delimiter to be a proper Dockerfile heredoc delimiter, not hidden inside a continued shell command.

Fix: replaced the inline heredoc in Linux package Dockerfiles with `printf '%s\n' ... > openocd.sh`.


## 2026-07-09 source layout fix

The package Dockerfiles now support both common ZIP extraction layouts:

- OpenOCD source files directly at the Docker build context root (`./bootstrap`).
- OpenOCD source files nested one level down (`./openocd/bootstrap`).

This fixes Docker builds that failed with `/bin/sh: ./bootstrap: not found` after copying packaging files into a parent directory.

## 2026-07-09 optional linux/arm64 build fix

`docker compose build` on Windows/amd64 failed with `exec /bin/sh: exec format error` when it tried to execute the linux/arm64 Alpine image without working ARM64 emulation.

Fixes:

- `docker-compose.yml` now builds only linux/amd64 and Windows x86_64 by default.
- `linux-arm64` is moved behind the optional Compose profile `arm64`.
- `docker-bake.hcl` default group excludes linux/arm64. Use `docker buildx bake all` for the full set.
- `scripts/build-linux-package.sh` builds linux/amd64 by default and only builds arm64 when `BUILD_ARM64=1` is set.

To build arm64 on an amd64 host, install/enable QEMU binfmt first:

```sh
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker compose --profile arm64 up --build
# or
docker buildx bake all
```


## 2026-07-09 bootstrap execution fix

The Linux and Windows packaging Dockerfiles now detect `bootstrap` using `-f` instead of `-x`, normalize CRLF line endings, and run it as `sh ./bootstrap`. This fixes Windows checkouts where Docker sees `./bootstrap` but direct execution fails with `/bin/sh: ./bootstrap: not found` due to shebang/line-ending handling.


## 2026-07-09 autotools CRLF normalization fix

The Linux and Windows packaging Dockerfiles now normalize CRLF line endings for Autotools input files before running `bootstrap`:

- `bootstrap`
- `configure.ac`
- `Makefile.am`
- `*.m4`
- `*.ac`
- `*.am`

This fixes `aclocal` / `autom4te` failures such as `AC_CONFIG_FILES is already registered` that can happen after extracting or editing the project on Windows with CRLF line endings.

## 2026-07-09 missing jimtcl submodule fix

The Linux and Windows packaging Dockerfiles now handle source ZIPs or shallow copies where the `jimtcl` submodule is missing. Before running `bootstrap`, they try `git submodule update --init --recursive jimtcl` when `.git` is present; if that still does not provide `jimtcl/autogen.sh`, they fetch Jim Tcl with `git clone --depth 1 https://github.com/msteveb/jimtcl.git jimtcl`. This fixes builds ending with `Skipping submodule setup` followed by `./bootstrap: line 58: ./autogen.sh: not found`.


## 2026-07-09 libjaylink autogen CRLF/executable fix

The package Dockerfiles now also normalize `autogen.sh` and `*.sh` files before running OpenOCD bootstrap. This fixes Windows checkouts where `src/jtag/drivers/libjaylink/autogen.sh` exists, but OpenOCD bootstrap fails with `./autogen.sh: not found` because the script has CRLF line endings or lost executable permissions.


## 2026-07-09 libconfuse MinGW examples fix

The Windows cross-build now builds only the libconfuse `src` subtree and installs the generated `libconfuse.pc` file manually. This keeps `ftdi_eeprom` support enabled through libftdi while avoiding libconfuse example programs that include Unix-only headers such as `<err.h>` and fail under MinGW.

## 2026-07-09 libjaylink fetch robustness fix

The Windows cross-build no longer depends only on repo.or.cz snapshot tarballs for libjaylink. Some Docker/Alpine builds failed with TLS EOF errors while fetching from repo.or.cz. The Windows Dockerfile now tries, in order:

1. `git clone --branch ${LIBJAYLINK_VERSION}` from `https://gitlab.zapb.de/libjaylink/libjaylink.git`
2. `git clone --branch ${LIBJAYLINK_VERSION}` from `https://github.com/damienhackett-eaton/libjaylink.git`
3. Retried curl download from repo.or.cz snapshot URLs

It also normalizes CRLF line endings and executable permissions for libjaylink `autogen.sh`/shell/autotools files before running configure.
