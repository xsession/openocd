# Enterprise layout migration

The packaging and documentation additions were consolidated to reduce root-level
clutter and make ownership boundaries explicit.

## Moved

| Previous location | Current location |
|---|---|
| `docker/Dockerfile.*` | `build/containers/*.Dockerfile` |
| `docker/prepare-openocd-source.sh` | `build/scripts/prepare-openocd-source.sh` |
| `docker/patch-jimtcl-mingw-aio.py` | `build/scripts/patch-jimtcl-mingw-aio.py` |
| `scripts/build-*.sh` | `build/scripts/build-*.sh` |
| `docker/data/dist/` | `artifacts/` |
| root build-review documents | `docs/development/` |
| `docker-compose.yml` | `compose.yaml` |

## Removed

The following runtime-container leftovers were removed because this repository now
uses containers only for reproducible package builds:

- runtime and remote-build Dockerfiles;
- OpenOCD container entrypoint;
- placeholder runtime configuration;
- duplicate udev rules;
- duplicate VS Code Windows readme;
- obsolete snapshot and container-image workflows.

## Compatibility

The user-facing commands remain simple:

```console
docker compose up --build
docker buildx bake all
```

The implementation details are now under `build/` and generated outputs are under
`artifacts/`.
