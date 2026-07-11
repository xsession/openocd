# Build troubleshooting

## `./bootstrap: not found`

Confirm the Docker context is the repository root and `.dockerignore` does not exclude `bootstrap`, `configure.ac`, `jimtcl`, or `src`.

```console
$ docker buildx build --no-cache --progress=plain -f build/containers/linux-package.Dockerfile .
```

The helper `build/scripts/prepare-openocd-source.sh` supports source files at the context root and one nested `openocd/` directory.

## Autotools errors on Windows checkouts

The preparation helper normalizes CRLF for Autotools and shell inputs. Configure Git to preserve LF for source scripts:

```powershell
git config core.autocrlf false
git config core.eol lf
git reset --hard
```

## Missing Jim Tcl or libjaylink files

Clone recursively:

```console
$ git submodule update --init --recursive
```

The Docker preparation script can fetch pinned commits, but a complete checkout is faster and more reproducible.

## `make -j0`

`JOBS=0` means automatic CPU detection in these Dockerfiles. They normalize it through `/usr/local/bin/docker-jobs`. Do not pass `make -j0` directly.

## `exec format error` for ARM64

Enable binfmt/QEMU or use a native ARM64 runner. See {doc}`linux`.

## Dependency download failures

Retry the build. Downloads use retry flags, but proxies and TLS inspection can still interrupt long uncached builds. For production CI, mirror source archives or pre-populate a BuildKit cache.

## Windows Jim Tcl AIO errors

The reviewed Windows build uses the OpenOCD-pinned Jim Tcl revision and applies `build/scripts/patch-jimtcl-mingw-aio.py`. Do not replace the submodule with arbitrary Jim Tcl `HEAD`, because its MinGW feature detection may differ.

## Compose builds but no artifacts appear

`docker compose build` only creates images. Export artifacts by running:

```console
$ docker compose up
```

or use:

```console
$ docker buildx bake
```
