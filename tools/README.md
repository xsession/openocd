# Repository tools

This directory contains maintainers' tools and integrations that are not part
of the OpenOCD runtime or installed script set.

## Ownership map

- `scripts/`: repository checks, release helpers, and small platform-neutral
  maintenance scripts.
- `docs/`: deterministic documentation generators and validation helpers.
- `release/`: release preparation and package verification helpers.
- `debug-servers/`: repo-local wrappers around external vendor debug servers.
- `ti/`: TI probe, target, and serial-programming helpers.
- `svd/`: SVD acquisition and transformation tools; generated SVD output is
  reviewed into the top-level `svd/` directory.
- `vscode/cortex-debug/`: the Cortex-Debug submodule and its upstream project
  files.

Vendor runtimes, extracted archives, package output, virtual environments, and
dependency caches are intentionally kept outside version control. See
`.gitignore` and the relevant tool README before adding generated content.

When adding a tool, place it under the narrowest existing owner directory and
add or update that directory's README. Do not put project-specific tools at
the repository root.
