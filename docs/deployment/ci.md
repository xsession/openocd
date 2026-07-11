# Continuous integration

The repository contains release workflows under `.github/workflows`.

Recommended jobs:

- Linux x86-64 package on `ubuntu-latest`.
- Linux ARM64 package through Buildx/QEMU or a native ARM64 runner.
- Windows x86-64 cross-package on `ubuntu-latest`.
- macOS x86-64 on an Intel macOS runner when available.
- macOS ARM64 on an Apple Silicon runner.
- Sphinx HTML documentation and link checking.

Use immutable dependency versions and pin action major versions. Upload package archives as workflow artifacts for pull requests, then attach them to GitHub Releases for tags.

For reproducibility, include these metadata values in the release notes:

```text
OpenOCD commit
Jim Tcl commit
libjaylink commit
Dockerfile dependency versions
Build runner architecture
```
