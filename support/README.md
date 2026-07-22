# Zephyr-Style Support Index

This directory organizes locally integrated MCU, board, programmer, catalog,
environment, and external-tool support using a Zephyr-inspired layout.

OpenOCD runtime files still live in their standard locations, such as `tcl/`,
`src/`, `contrib/`, and `docs/`. The files here are metadata indexes that make
support easier to browse, audit, package, and eventually upstream in smaller
batches.

## Layout

```text
support/
|-- boards/<vendor>/<board>/
|   |-- board.yml
|   |-- README.md
|   `-- support/
|-- catalogs/<source>/
|   |-- parts.yml
|   `-- programmers.yml
|-- environments/<family>/
|   `-- programming.yml
|-- soc/<vendor>/<soc-or-family>/
|   |-- soc.yml
|   `-- README.md
|-- programmers/<vendor>/<programmer>/
|   |-- programmer.yml
|   `-- README.md
|-- modules/<source-or-tool>/
|   |-- module.yml
|   `-- README.md
`-- vendors/<vendor>/
    `-- vendor.yml
```

## Rules

1. Keep OpenOCD runtime scripts in `tcl/` so install and package hooks keep
   working.
2. Put human-readable ownership and status metadata in `support/`.
3. Every board entry must point to its target script and programmer/interface
   script.
4. Every programmer entry must state whether support is native, FTDI/CMSIS-DAP
   based, or delegated to an external executable.
5. Every module entry must pin the upstream source and clarify whether files
   are imported, generated, or delegated.
6. Environment entries tie together catalogs, runtime commands, fallback tools,
   and native backend queues for a programming/debug family.
7. Do not copy a whole external repository into `support/`; use it as an audit
   map.

## Status Keywords

| Status | Meaning |
| --- | --- |
| `integrated` | Present in this tree and validated by build or config-load tests. |
| `delegated` | Available through an external tool bridge. |
| `experimental` | Loads or builds, but needs hardware validation. |
| `deferred` | Recorded for a later native backend batch. |
| `blocked` | Cannot proceed without protocol docs, hardware, or license clarity. |
