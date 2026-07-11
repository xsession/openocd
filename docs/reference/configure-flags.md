# Configure flags

Default Linux flags:

```text
--enable-ftdi
--enable-stlink
--enable-cmsis-dap
--enable-jlink
--enable-jimtcl-maintainer
--enable-internal-jimtcl
```

Default Windows flags also enable bundled libjaylink:

```text
--enable-internal-libjaylink
```

Override per platform:

```console
$ LINUX_CONFIGURE_FLAGS="..." docker compose build linux-amd64
$ WINDOWS_CONFIGURE_FLAGS="..." docker compose build windows-x86_64
```

PowerShell:

```powershell
$env:WINDOWS_CONFIGURE_FLAGS = "--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-libjaylink --enable-internal-jimtcl"
docker compose build windows-x86_64
```

The Dockerfiles append `--disable-werror` for portable release builds so compiler-version-specific warnings do not block packaging. Maintainer CI should still run a separate strict warning build.
