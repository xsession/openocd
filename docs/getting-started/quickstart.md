# Quick start

The default build produces Linux x86-64 and Windows x86-64 packages.

## Build package images

```console
$ docker compose build
```

This validates and builds the package images but does not copy artifacts to the host.

## Export packages

```console
$ docker compose up
```

To rebuild and export in one command:

```console
$ docker compose up --build
```

Expected files:

```text
artifacts/linux/amd64/openocd-linux-x86_64.tar.gz
artifacts/windows/openocd-windows-x86_64.zip
```

## Buildx Bake alternative

Bake writes artifacts directly and is usually the cleanest CI interface:

```console
$ docker buildx bake
```

Build every Docker-supported target, including Linux ARM64:

```console
$ docker buildx bake all
```

See {doc}`../deployment/troubleshooting` before enabling ARM64 emulation on an x86-64 Windows host.
