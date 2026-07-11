# Artifact layout and verification

Generated files are under `artifacts` and should not be committed.

```text
artifacts/
├── linux/
│   ├── amd64/
│   └── arm64/
├── windows/
└── macos/
```

## Verify archives

Linux/macOS:

```console
$ sha256sum openocd-*.tar.gz
$ tar -tzf openocd-linux-x86_64.tar.gz | head
```

Windows PowerShell:

```powershell
Get-FileHash .\openocd-windows-x86_64.zip -Algorithm SHA256
Expand-Archive .\openocd-windows-x86_64.zip -DestinationPath .\verify
.\verify\openocd-windows-x86_64\openocd.cmd --version
```

## Release checklist

1. Build from a clean checkout with initialized submodules.
2. Record the OpenOCD commit SHA.
3. Build every intended architecture.
4. Run `openocd --version` from each package.
5. Smoke-test at least one supported adapter per operating system.
6. Generate SHA-256 checksums.
7. Publish archives and checksums together.
