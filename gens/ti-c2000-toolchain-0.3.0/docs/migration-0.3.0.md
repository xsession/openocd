# Migration to 0.3.0

Release 0.3.0 merges the previously separate SVD/debug repository, Renode
backend, and XDS100 OpenOCD bundle.

## Path changes

| Previous artifact | 0.3.0 location |
|---|---|
| `ti-c2000-debug-svd.zip` | unified repository root |
| `c2000-debug-0.2.0.vsix` | `extension/c2000-debug-0.3.0.vsix` |
| `openocd-xds100v2-v3-support.zip` | `openocd/` |
| standalone XDS100 validation report | `reports/openocd-xds100v2-v3-validation.md` |

## Stable interfaces

- Debug type remains `c2000-debug`.
- CLI command remains `ti-svd`.
- Existing CCS and Renode launch configurations remain compatible.
- OpenOCD backend still attaches through its telnet port.

## Removed stale outputs

The release no longer includes old `0.1.0` or `0.2.0` VSIX files.
