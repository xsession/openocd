# OpenOCD source layout Docker packaging fix

Use this direct replacement package if Docker fails with:

```text
/bin/sh: ./bootstrap: not found
```

The packaging Dockerfiles now support both layouts:

- source files at the build context root: `./bootstrap`
- source files nested one level down: `./openocd/bootstrap`

From your current project root:

```powershell
Expand-Archive .\openocd-source-layout-replacement-files.zip -DestinationPath .\_replacement
.\_replacement\openocd-source-layout-replacement-files\install-overwrite.ps1
docker compose up --build
```

Manual copy also works: copy the contents of `files/` over your project root.
