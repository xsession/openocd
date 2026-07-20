# Repository layout

The repository separates upstream OpenOCD source, project documentation, Docker
build infrastructure, and generated artifacts.

```text
.
|-- .github/              CI workflows and contribution templates
|-- artifacts/            Generated packages; never committed
|-- contrib/              Upstream utilities and integration assets
|-- doc/                  Upstream Texinfo and man-page reference
|-- docker/               Dockerfiles, Compose/Bake files, scripts, and runtime data
|-- docs/                 Sphinx/MyST operational documentation
|-- src/                  OpenOCD implementation
|-- tcl/                  OpenOCD runtime scripts
|-- testing/              Test infrastructure
|-- tools/                Upstream maintenance tools
`-- README.DOCKER_PACKAGING.md
```

## Ownership boundaries

- Product source changes belong in `src/`, `tcl/`, and the existing upstream
  build-system files.
- Packaging and release automation belongs in `docker/` and `.github/workflows/`.
- User and operator documentation belongs in `docs/`.
- Generated packages belong in `artifacts/` and must not be committed.
- Historical implementation notes belong in `docs/development/change-history.md`,
  not in the repository root.
