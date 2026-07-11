# Linux packages

## Linux x86-64

```console
$ ./build/scripts/build-linux-package.sh
```

The default output is:

```text
artifacts/linux/amd64/openocd-linux-x86_64.tar.gz
```

## Linux ARM64

On an ARM64 host, build directly. On an x86-64 host, install QEMU/binfmt support first:

```console
$ docker run --privileged --rm tonistiigi/binfmt --install arm64
$ docker compose --profile arm64 up --build
```

Or with the helper script:

```console
$ BUILD_ARM64=1 ./build/scripts/build-linux-package.sh
```

```{warning}
`exec /bin/sh: exec format error` means the Docker engine cannot execute the ARM64 base image. It is an emulation/runner problem, not an OpenOCD source failure.
```

## Install

```console
$ tar -xzf openocd-linux-x86_64.tar.gz
$ ./openocd-linux-x86_64/openocd.sh --version
```

Move the directory wherever desired. The wrapper resolves `bin/openocd` relative to itself.
