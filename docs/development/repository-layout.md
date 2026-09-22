# Repository layout

The repository separates upstream OpenOCD source, runtime scripts, project
feature tooling, documentation, Docker build infrastructure, and generated
artifacts. The paths below are the maintained interfaces for contributors;
build-critical upstream paths are intentionally kept stable.

```text
.
|-- .github/              CI workflows and contribution templates
|-- artifacts/            Generated packages; ignored except for .gitkeep
|-- contrib/              Upstream utilities and integration assets
|-- doc/                  Upstream Texinfo and man-page reference
|-- docker/               Dockerfiles, Compose/Bake files, scripts, and runtime data
|-- docs/                 MkDocs documentation, C4 model, and design records
|-- examples/             Ready-made OpenOCD usage and programming examples
|-- samples/              Legacy/upstream sample configurations retained for compatibility
|-- gens/                 Ignored staging area for generated/source-drop imports
|-- src/                  OpenOCD implementation
|-- svd/                  Curated committed SVD files
|-- tcl/                  OpenOCD runtime scripts
|-- testing/              Test infrastructure
|-- tools/                Maintenance tools plus curated TI/Microchip feature tooling
|-- udev/                 Linux USB permission rules
`-- docs/deployment/docker-packaging.md   (Docker packaging guide)
```

## Ownership boundaries

- Product source changes belong in `src/`, `tcl/`, and the existing upstream
  build-system files. Do not move these paths: installed package layout,
  Zephyr/OpenOCD integrations, and external scripts depend on them.
- Packaging and release automation belongs in `docker/`, `.github/workflows/`,
  and `tools/release/`.
- Small, user-facing configuration examples belong in `examples/`; hardware
  support metadata belongs in `support/` and runtime configs belong in `tcl/`.
- User and operator documentation belongs in `docs/`.
- Runtime architecture and C4 views belong in `docs/architecture/`; source
  references in those pages must point to real implementation paths.
- Curated vendor/tooling support belongs under `tools/<vendor>/`; generated
  feature drops stay in ignored `gens/` until reviewed.
- Debugger data that is intentionally committed belongs in `svd/`; generator
  source belongs in `tools/`.
- Generated packages belong in `artifacts/` and must not be committed.
- Historical implementation notes belong in `docs/development/change-history.md`.
  The current CI handoff is retained in the root `CI_ISSUES_AND_FIXES.md`
  because it documents the repaired workflow failures.

See [Source catalog](source-catalog.md) for the detailed category map.
