# Repository layout

The repository separates upstream OpenOCD source, runtime scripts, project
feature tooling, documentation, Docker build infrastructure, and generated
artifacts.

```text
.
|-- .github/              CI workflows and contribution templates
|-- artifacts/            Generated packages; never committed
|-- contrib/              Upstream utilities and integration assets
|-- doc/                  Upstream Texinfo and man-page reference
|-- docker/               Dockerfiles, Compose/Bake files, scripts, and runtime data
|-- docs/                 Sphinx/MyST operational documentation
|-- examples/             Ready-made OpenOCD usage and programming examples
|-- gens/                 Ignored staging area for generated/source-drop imports
|-- src/                  OpenOCD implementation
|-- svd/                  Curated committed SVD files
|-- tcl/                  OpenOCD runtime scripts
|-- testing/              Test infrastructure
|-- tools/                Maintenance tools plus curated TI/Microchip feature tooling
|-- udev/                 Linux USB permission rules
`-- README.DOCKER_PACKAGING.md
```

## Ownership boundaries

- Product source changes belong in `src/`, `tcl/`, and the existing upstream
  build-system files.
- Packaging and release automation belongs in `docker/`, `.github/workflows/`,
  and `tools/release/`.
- User and operator documentation belongs in `docs/`.
- Curated vendor/tooling support belongs under `tools/<vendor>/`; generated
  feature drops stay in ignored `gens/` until reviewed.
- Debugger data that is intentionally committed belongs in `svd/`; generator
  source belongs in `tools/`.
- Generated packages belong in `artifacts/` and must not be committed.
- Historical implementation notes belong in `docs/development/change-history.md`,
  not in the repository root.

See [Source catalog](source-catalog.md) for the detailed category map.
