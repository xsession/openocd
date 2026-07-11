# Build-system design

## Components

| File | Responsibility |
|---|---|
| `build/containers/linux-package.Dockerfile` | Native Linux package builds |
| `build/containers/windows-cross.Dockerfile` | MinGW-w64 Windows cross-build |
| `build/scripts/prepare-openocd-source.sh` | Source layout, submodule, line-ending preparation |
| `build/scripts/patch-jimtcl-mingw-aio.py` | Isolated Jim Tcl MinGW compatibility patch |
| `compose.yaml` | Developer-friendly image build and artifact copy |
| `docker-bake.hcl` | Direct multi-target artifact export |
| `build/scripts/build-*.sh` | Stable command-line wrappers |

## Compose versus Bake

Use Compose when developers want familiar commands and mounted output directories:

```console
$ docker compose up --build
```

Use Bake for CI and direct local exporters:

```console
$ docker buildx bake
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
