# Output layout

| Target | Archive |
|---|---|
| Linux x86-64 | `artifacts/linux/amd64/openocd-linux-x86_64.tar.gz` |
| Linux ARM64 | `artifacts/linux/arm64/openocd-linux-aarch64.tar.gz` |
| Windows x86-64 | `artifacts/windows/openocd-windows-x86_64.zip` |
| macOS x86-64 | `artifacts/macos/openocd-macos-x86_64.tar.gz` |
| macOS ARM64 | `artifacts/macos/openocd-macos-arm64.tar.gz` |

Each OpenOCD archive contains a `bin` directory and `share/openocd` data. Keep them together; moving only the executable can break script discovery.
