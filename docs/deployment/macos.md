# macOS packages

macOS binaries should be built on macOS. Linux containers cannot produce fully supported native, signed macOS binaries because Apple SDKs and tooling are not redistributable in a normal Docker image.

## Native build

Install prerequisites:

```console
$ xcode-select --install
$ brew install autoconf automake libtool pkg-config libusb hidapi libftdi libjaylink texinfo
```

Then run:

```console
$ ./docker/scripts/build-macos-package.sh
```

The script selects the package architecture from the host and writes to:

```text
artifacts/macos/openocd-macos-x86_64.tar.gz
artifacts/macos/openocd-macos-arm64.tar.gz
```

## Universal binaries

For a universal package, build on both architectures and combine Mach-O executables with `lipo`. Keep architecture-specific Homebrew dependencies separate during each build. The release workflow intentionally publishes separate archives because they are simpler to test and troubleshoot.

## Signing and notarization

Unsigned local tools work for most developer use. Public distribution may require Developer ID signing and notarization. Keep signing identities and notarization credentials in protected CI secrets, never in the repository.
