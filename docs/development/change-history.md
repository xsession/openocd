# Docker runtime and cross-build fixes

## Runtime config lookup fix

The container failed with:

```text
embedded:startup.tcl:88: Error: Can't find config/default.cfg
```

The Compose file previously mounted `./docker/data/config` to `/work/config`, but the repository contains the default config at `./config/default.cfg`. Also, OpenOCD resolves `-f config/default.cfg` through its script search path, not only through the shell working directory.

Fixes:

- `docker/compose.runtime.yaml` mounts `./data/config:/work/config:ro`.
- `docker/scripts/openocd-entrypoint.sh` adds `-s /work` before runtime config arguments.
- Compose keeps `command: ["-f", "config/default.cfg"]`, which now resolves to `/work/config/default.cfg`.

## Alpine and Werror fix

The Linux Dockerfiles use Alpine and force `--disable-werror` directly in the configure command, so Compose/build-arg overrides cannot accidentally re-enable fatal warnings.

## Windows cross package

Added:

- `docker/Dockerfile.windows-cross`
- `docker/scripts/build-windows-cross.sh`
- `make package-windows`

The Windows artifact is exported to:

```text
artifacts/windows
```

Expected output:

```text
artifacts/windows/openocd-windows-x86_64.zip
```

Build it from the repository root with:

```sh
make package-windows
```

or on Windows PowerShell:

```powershell
$env:OUT_DIR="artifacts/windows"
sh docker/scripts/build-windows-cross.sh
```

## 2026-07-09 Windows cross-build JOBS=0 fix

The Windows cross-compile Dockerfile previously used commands such as:

```sh
make -j"${JOBS:-$(nproc)}"
```

Because the Dockerfile default was `ARG JOBS=0`, shell parameter expansion did not fall back to `nproc`; it emitted `make -j0`, which GNU Make rejects.

The Dockerfile now installs a small `/usr/local/bin/docker-jobs` helper and uses:

```sh
make -j"$(docker-jobs)"
cmake --build ... --parallel "$(docker-jobs)"
```

`JOBS=0` and empty `JOBS` now both mean "use all available CPUs". A positive integer still limits parallelism, for example:

```sh
docker buildx build -f docker/Dockerfile.windows-cross --build-arg JOBS=4 --target export --output type=local,dest=artifacts/windows .
```

Do not use `docker/Dockerfile.windows-cross` as the runtime service Dockerfile in `docker/compose.runtime.yaml`. It is a package/export Dockerfile with a `scratch` export stage. Use:

```sh
make package-windows
```

or:

```sh
sh docker/scripts/build-windows-cross.sh
```

The expected package output remains:

```text
artifacts/windows/openocd-windows-x86_64.zip
```

## 2026-07-11 Docker build-context correction

- Stopped excluding the enterprise `build/` directory from `.dockerignore`.
- Kept generated `build-*` trees excluded.
- Excluded generated package artifacts and rendered documentation from the Docker context.
- The Docker files now live under `docker/`; use `docker/compose.yaml` for packaging and `docker/compose.runtime.yaml` for the runtime container.
