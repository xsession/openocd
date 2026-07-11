# OpenOCD build and deployment guide

This repository extends OpenOCD with reproducible packaging for the main desktop platforms. Use this site to choose the right build path, create portable packages, install them, and connect a debugger to target hardware.

```{admonition} What Docker does here
:class: important
Docker is used as a **build environment**, not as the normal OpenOCD runtime. It produces Linux and Windows packages under `artifacts`. macOS packages are built natively on macOS or in GitHub Actions.
```

## Start here

| Goal | Recommended path |
|---|---|
| Build Linux x86-64 and Windows x86-64 on a PC | {doc}`getting-started/quickstart` |
| Build Linux ARM64 | {doc}`deployment/linux` |
| Build macOS Intel and Apple Silicon packages | {doc}`deployment/macos` |
| Install a generated package | {doc}`deployment/artifacts` |
| Run OpenOCD with a probe and target | {doc}`usage/first-session` |
| Fix a failed package build | {doc}`deployment/troubleshooting` |
| Understand or change the build system | {doc}`development/build-system` |

```{toctree}
:hidden:
:maxdepth: 2

getting-started/overview
getting-started/quickstart
getting-started/prerequisites
deployment/index
deployment/linux
deployment/windows
deployment/macos
deployment/artifacts
deployment/ci
deployment/troubleshooting
usage/first-session
usage/configuration
usage/debuggers
development/build-system
development/repository-layout
development/enterprise-layout-migration
development/documentation-architecture
development/documentation
development/build-review
reference/output-layout
reference/configure-flags
reference/legacy-manual
```
