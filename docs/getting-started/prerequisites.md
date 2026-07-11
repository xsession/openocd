# Prerequisites

## All hosts

- Git with submodule support.
- Docker Desktop or Docker Engine with Buildx.
- At least 8 GB free disk space for uncached multi-platform builds.
- A checkout that includes the `jimtcl` and bundled `libjaylink` submodules, or network access during the Docker build so the preparation helper can fetch pinned revisions.

Clone recursively when possible:

```console
$ git clone --recursive https://github.com/xsession/openocd.git
$ cd openocd
```

For an existing checkout:

```console
$ git submodule update --init --recursive
```

## Windows host

Use PowerShell 7 or Windows PowerShell with Docker Desktop using Linux containers. Keep the repository on a local NTFS drive rather than a slow network share.

```powershell
Docker version
docker buildx version
docker compose version
```

## Linux host

Add the current user to the Docker group or run Docker commands with appropriate privileges. ARM64 emulation is optional.

## macOS host

Docker can build Linux and Windows packages. Native Xcode Command Line Tools and Homebrew are needed for macOS binaries.
