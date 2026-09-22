# Documentation architecture decision

## Decision

Use **MkDocs Material with Markdown** as the primary build/deployment documentation system. Preserve the existing Texinfo manual and Doxygen configuration as specialist references.

## Why not Typst as the primary system

Typst is well suited to polished PDF output, but this project needs a searchable website, stable cross-references, strict validation, versioned pages, and a future path to Doxygen API integration. MkDocs Material provides the site navigation, search, responsive layout, and strict Markdown build directly.

## Content boundaries

- `README.md`: concise landing page and working build commands.
- `docs/`: task-oriented packaging, installation, runtime, and troubleshooting guide built by MkDocs.
- `docs/architecture/`: source-grounded C4 context, container, component,
  deployment, build, and decision views.
- `doc/openocd.texi`: complete OpenOCD command reference.
- `Doxyfile.in`: implementation/API reference.
- `docs/development/change-history.md`: historical engineering record, not onboarding documentation.
