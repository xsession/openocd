# Docker packaging build review

## Corrected defects

- Replaced the malformed `Dockerfile.windows-cross` section produced by an inline Python heredoc.
- Kept Jim Tcl AIO enabled on MinGW by applying a standalone, idempotent compatibility script.
- Pinned fallback Jim Tcl to OpenOCD's recorded `0.83` submodule commit:
  `f160866171457474f7c4d6ccda70f9b77524407e`.
- Pinned fallback libjaylink to OpenOCD's recorded `0.3.1` submodule commit:
  `0d23921a05d5d427332a142d154c213d0c306eb1`.
- Removed the redundant separately-built Windows libjaylink dependency and enabled
  OpenOCD's bundled libjaylink using `--enable-internal-libjaylink`.
- Preserved `ftdi_eeprom` by cross-building static libconfuse and libftdi.
- Kept Linux ARM64 optional for Docker Desktop hosts without binfmt/QEMU.
- Split Linux and Windows configure flags in Compose and Bake.
- Kept Compose for package image execution/export and Bake for direct local output.

## Commands

```powershell
docker compose -f docker/compose.yaml build --no-cache
docker compose -f docker/compose.yaml up
```

Direct export:

```powershell
docker buildx bake -f docker/docker-bake.hcl
```

Optional ARM64:

```powershell
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker buildx bake -f docker/docker-bake.hcl all
```
