# Build-system design

## Components

| File | Responsibility |
|---|---|
| `docker/Dockerfile.linux-package` | Native Linux package builds |
| `docker/Dockerfile.windows-cross` | MinGW-w64 Windows cross-build |
| `docker/scripts/prepare-openocd-source.sh` | Source layout, submodule, line-ending preparation |
| `docker/scripts/patch-jimtcl-mingw-aio.py` | Isolated Jim Tcl MinGW compatibility patch |
| `docker/compose.yaml` | Developer-friendly image build and artifact copy |
| `docker/docker-bake.hcl` | Direct multi-target artifact export |
| `docker/scripts/build-*.sh` | Stable command-line wrappers |

## Compose versus Bake

Use Compose when developers want familiar commands and mounted output directories:

```console
$ docker compose -f docker/compose.yaml up --build
```

Use Bake for CI and direct local exporters:

```console
$ docker buildx bake -f docker/docker-bake.hcl
```

Compose cannot use the Bake-only `output` property in a service build definition. Therefore package Dockerfiles expose both:

- `package`: runnable image that copies `/out` to mounted `/dist`.
- `export`: `scratch` stage for Buildx `type=local` output.

## Dependency policy

- Pin source dependency versions or commits.
- Keep platform compatibility patches in standalone scripts.
- Avoid inline code-generation heredocs in Dockerfiles.
- Keep downloaded examples/tests out of cross-builds when they require host-only headers.
- Run package smoke tests after archive creation.
