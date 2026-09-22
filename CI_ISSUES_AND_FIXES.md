# OpenOCD CI Issues and Fixes

## Scope

This report documents the failures found in the OpenOCD repository at commit
`8d15bb2244b4cfdf7c0ac20521e6c642c7f67ac0` (`Reorganize the sources`) and the
fixes applied in the working tree.

The primary failure investigated was:

- [Microchip programmer bridge run 35693830487](https://github.com/xsession/openocd/actions/runs/35693830487)

The same commit also failed the Docker, package, snapshot, and documentation
workflows. The failures were independent and are described below.

## Issue 1: nonexistent recursive submodule

### Symptom

The Docker, package, and documentation jobs failed during
`actions/checkout@v4` before their build steps ran:

```text
remote: Repository not found.
fatal: repository 'https://github.com/xsession/open_microchip_tools.git/' not found
fatal: clone of 'https://github.com/xsession/open_microchip_tools.git' into submodule path 'externals/open_microchip_tools' failed
```

### Cause

`.gitmodules` declared `externals/open_microchip_tools` as a recursive
submodule, but the referenced GitHub repository does not exist. The commit also
contained the corresponding gitlink in the repository tree.

### Fix

- Removed the invalid `externals/open_microchip_tools` entry from `.gitmodules`.
- Removed the stale `externals/open_microchip_tools` gitlink.
- Removed obsolete distribution-cleanup paths from `Makefile.am`.

The generated Microchip SVD files and current OpenOCD source remain in the
repository. The missing external project is not required by the CI test or
build paths.

### Verification

Recursive submodule initialization now succeeds for the three valid
submodules:

- `jimtcl`
- `src/jtag/drivers/libjaylink`
- `tools/vscode/cortex-debug`

## Issue 2: stale Microchip SVD test path

### Symptom

The Microchip workflow failed with:

```text
FileNotFoundError: .../svd/dspic30f5011.svd
```

### Cause

The test searched directly under `svd/`, while the committed files are stored
under `svd/microchip/`:

```text
svd/microchip/dspic30f5011.svd
svd/microchip/dspic33fj128mc802.svd
svd/microchip/dspic33fj128mc804.svd
svd/microchip/dspic33ep128gm604.svd
```

### Fix

Updated `testing/microchip_programmer/test_microchip_programmer.py` to use
`svd/microchip/`. The Microchip workflow path filters now also include
`svd/microchip/**`, so changes to the tested SVD inputs trigger the workflow.
The SVD README was corrected to describe the actual directory layout.

### Verification

The previously failing SVD test passes locally.

## Issue 3: missing libusb include propagation in the cross-build

### Symptom

The Windows snapshot build reached compilation and then failed at:

```text
src/jtag/drivers/libusb_helper.h:12:10: fatal error: libusb.h: No such file or directory
```

The failing translation unit was `src/avr/programmers/usbasp.c`.

### Cause

The AVR library contains a libusb-backed USBasp implementation, but
`src/avr/Makefile.am` did not propagate the configured `LIBUSB1_CFLAGS` to the
AVR target. The JTAG driver library had the flags, while the AVR library did
not.

### Fix

Added conditional `LIBUSB1_CFLAGS` and `LIBUSB1_LIBS` propagation to the AVR
library in `src/avr/Makefile.am`.

This makes the cross-build use the sysroot's
`include/libusb-1.0/libusb.h` location consistently.

## Issue 4: parallel Git metadata race and lightweight-tag handling

### Symptoms

The snapshot build emitted both of these errors while compiling in parallel:

```text
fatal: No annotated tags can describe '8d15bb2244b4cfdf7c0ac20521e6c642c7f67ac0'.
However, there were unannotated tags: try --tags.

fatal: Unable to create '.../.git/index.lock': File exists.
```

### Causes

Two build-time version paths were unsafe for this checkout:

1. `src/Makefile.am` used `git describe` without `--tags`, so a lightweight
   `v0.13.0` tag was ignored.
2. `guess-rev.sh` called `git update-index --refresh` every time it was invoked.
   Parallel compiler jobs invoked the script concurrently against the same
   repository index.

### Fix

- Changed the build-time version lookup to `git describe --tags --always`.
- Made `guess-rev.sh` use `GIT_OPTIONAL_LOCKS=0` for read-only Git queries.
- Removed the concurrent `git update-index` operation.
- Made the dirty-tree check use `git diff-index --quiet`.
- Made the fallback tag lookup in `contrib/cross-build.sh` use
  `--tags --always --dirty`.

### Verification

Twenty-four concurrent `guess-rev.sh` invocations completed without an index
lock error. Lightweight tags are now recognized correctly.

## Issue 5: documentation workflow was tied to the old site generator

### Symptoms

The documentation workflow and Docker image still invoked Sphinx and referred
to the previous `build/` container/script locations. The Markdown corpus also
contained Sphinx/MyST directives that MkDocs cannot render, and runtime support
tables could drift away from the checked-in board, FPGA, cable, SVD, and board
metadata files.

### Fix

- Replaced the Sphinx/MyST/Furo dependency set with MkDocs Material and
  `pymdown-extensions`.
- Added `mkdocs.yml` with explicit navigation for the complete documentation
  corpus, including the 24-lab OpenOCD course.
- Converted Sphinx-only directives and cross-references to MkDocs Markdown and
  admonitions.
- Kept `doc/openocd.texi` and `Doxyfile.in` as specialist manual/API paths
  instead of duplicating them in the site.
- Added `tools/docs/generate_support_tables.py`; CI checks that its generated
  support matrix is current before running `mkdocs build --strict`.
- Updated the documentation workflow, Dockerfile, and helper script to use the
  `docker/` layout and MkDocs commands.

### Verification

- `python3 -m mkdocs build --strict --site-dir /tmp/openocd-mkdocs-site-final`
- `python3 tools/docs/generate_support_tables.py --check`
- Relative-link validation across all 99 Markdown files.
- No remaining Sphinx/MyST directives in the MkDocs site.

## Issue 6: architecture was not discoverable from the documentation site

### Symptoms

The repository had useful source catalogs and vendor notes, but no coherent
system context, runtime container model, component call flow, deployment view,
or source-to-build map. The navigation also presented historical audit pages as
one flat list, making the maintainer path difficult to follow.

### Fix

- Added a source-grounded C4 section under `docs/architecture/` with context,
  container, component, deployment, build/release, source-map, and decision
  pages.
- Grouped development navigation into integration/tooling, vendor-audit, and
  historical/merge sections.
- Linked the architecture model from `README.md`, `CONTRIBUTING.md`, and the
  documentation home page.
- Removed the obsolete `docs/conf.py` Sphinx configuration.
- Clarified the distinction between curated `examples/` and retained legacy
  `samples/`.

### Verification

- The strict MkDocs build includes all C4 pages and diagrams.
- All 99 Markdown files have resolvable relative links.
- The generated support matrix remains current.

## Validation performed

The following checks were completed after the fixes:

- Microchip Python test file: the three non-Tcl integration tests pass.
- Shell syntax validation for `guess-rev.sh` and `contrib/cross-build.sh`.
- Python bytecode compilation for the Microchip test file.
- YAML parsing for all six GitHub workflow files.
- `git diff --check`.
- Recursive initialization of all remaining submodules.
- Concurrent Git version detection to exercise the former lock race.
- MkDocs strict build and generated support-matrix drift check.
- Relative Markdown link validation across the site.

The local container does not provide `tclsh` or `libtool`, so the ten
Tcl-backed Microchip tests and a native Autotools build could not be executed
locally. In the referenced GitHub run, those ten Tcl-backed tests had already
passed before the stale SVD path caused the job to fail.

GitHub Actions was not rerun from this workspace because the corrected changes
were not pushed to a remote branch.

## Issue 7: documentation was not published to GitHub Pages

### Symptom

The MkDocs workflow built an HTML artifact for inspection, but there was no
workflow that uploaded the generated site to GitHub Pages. Documentation was
therefore not published after a successful build.

### Fix

Added `.github/workflows/pages.yml` with separate build and deploy jobs. The
workflow:

- runs for documentation changes on `master` and `main`, or by manual dispatch;
- performs the generated-support-table check and strict MkDocs build;
- uploads only the generated `site/` directory with
  `actions/upload-pages-artifact`;
- deploys through the protected `github-pages` environment with the minimum
  Pages and OIDC permissions.

The repository Pages setting must use **GitHub Actions** as its publishing
source. The expected public URL is <https://xsession.github.io/openocd/>.

### Verification

- The new workflow YAML parses with the other repository workflows.
- The strict MkDocs build succeeds locally with the Pages output layout.
- The Pages setup and failure modes are documented in
  `docs/deployment/ci.md`.

## Changed files

- `.github/workflows/microchip-programmers.yml`
- `.gitmodules`
- `Makefile.am`
- `contrib/cross-build.sh`
- `guess-rev.sh`
- `src/Makefile.am`
- `src/avr/Makefile.am`
- `svd/README.md`
- `testing/microchip_programmer/test_microchip_programmer.py`
- `mkdocs.yml`
- `docs/requirements.txt`
- `tools/docs/generate_support_tables.py`
- `docs/reference/support-matrix.md`
- `docs/architecture/*.md`
- `docs/conf.py` removed
- `.github/workflows/docs.yml`
- `.github/workflows/pages.yml`
- `docker/Dockerfile.docs`
- Removed gitlink: `externals/open_microchip_tools`
