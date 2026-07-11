# OpenOCD: reproducible multi-platform packages

This repository is an OpenOCD fork with a reviewed packaging layer for Linux, Windows, and macOS. Docker is used to build portable Linux and Windows archives; macOS packages are built natively or in CI.

## Build the default packages

```console
$ git clone --recursive https://github.com/xsession/openocd.git
$ cd openocd
$ docker compose up --build
```

Artifacts:

```text
artifacts/linux/amd64/openocd-linux-x86_64.tar.gz
artifacts/windows/openocd-windows-x86_64.zip
```

Build Linux ARM64 when the Docker engine has ARM64 emulation or runs natively on ARM64:

```console
$ docker compose --profile arm64 up --build
```

Build every Docker-supported package with direct local export:

```console
$ docker buildx bake all
```

## Documentation

The task-oriented guide is under [`docs/`](docs/index.md):

- [Quick start](docs/getting-started/quickstart.md)
- [Windows package](docs/deployment/windows.md)
- [Linux packages](docs/deployment/linux.md)
- [macOS packages](docs/deployment/macos.md)
- [Build troubleshooting](docs/deployment/troubleshooting.md)
- [First debug session](docs/usage/first-session.md)
- [Build-system design](docs/development/build-system.md)

Build the searchable Sphinx site:

```console
$ ./build/scripts/build-docs.sh
```

Equivalent commands:

```console
$ docker buildx bake documentation
$ docker compose --profile docs up --build docs
```

The upstream command reference remains in [`doc/openocd.texi`](doc/openocd.texi), and source API documentation remains configured by [`Doxyfile.in`](Doxyfile.in).

## Project status

The packaging flow produces portable archives and keeps platform-specific compatibility fixes isolated in reviewed helper scripts. See [build review](docs/development/build-review.md) for the current build design and [change history](docs/development/change-history.md) for historical fixes.

## License

OpenOCD is licensed under GNU GPL v2. See [`COPYING`](COPYING) and [`LICENSES/`](LICENSES/).
