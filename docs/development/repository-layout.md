# Repository layout

The repository separates upstream OpenOCD source, project documentation, build
infrastructure, and generated artifacts.

```text
.
├── .github/              CI workflows and contribution templates
├── artifacts/            Generated packages; never committed
├── build/
│   ├── containers/       Docker build definitions
│   └── scripts/          Stable developer and CI entry points
├── contrib/              Upstream utilities and integration assets
├── doc/                  Upstream Texinfo and man-page reference
├── docs/                 Sphinx/MyST operational documentation
├── src/                  OpenOCD implementation
├── tcl/                  OpenOCD runtime scripts
├── testing/              Test infrastructure
├── tools/                Upstream maintenance tools
├── compose.yaml          Local package-builder orchestration
└── docker-bake.hcl       Buildx package export targets
```

## Ownership boundaries

- Product source changes belong in `src/`, `tcl/`, and the existing upstream
  build-system files.
- Packaging and release automation belongs in `build/` and `.github/workflows/`.
- User and operator documentation belongs in `docs/`.
- Generated packages belong in `artifacts/` and must not be committed.
- Historical implementation notes belong in `docs/development/change-history.md`,
  not in the repository root.
