# Cortex-Debug and C2000 compatibility

## Arm targets

MSPM0C1103 and the F28M35x Cortex-M3 subsystem remain normal Cortex-Debug targets.
The generator validates a Cortex-M CPU entry, byte addressing and a valid SVD tree
for those profiles.

```sh
ti-svd vscode-config mspm0c1103 --servertype openocd
ti-svd vscode-config tms320f28m35x_m3 \
  --servertype external \
  --gdb-target localhost:3333
```

Current configurations use `svdPath`. `--legacy-svd-file` emits the older `svdFile`
property when required by an old extension release.

## C28x targets

F28069, F280049 and the F28M35x C28x subsystem are handled by the repository's
`c2000-debug` extension:

```sh
ti-svd vscode-config tms320f28069 \
  --backend ccs \
  --ccs-root C:/ti/ccs2040 \
  --ccxml '${workspaceFolder}/targetConfigs/F28069_XDS110.ccxml'
```

The SVD peripheral UI is supplied by the standalone MCU Peripheral Viewer, which
can work with any debugger that implements the Microsoft Debug Adapter Protocol.
The C2000 adapter implements DAP memory reads/writes and consumes the same
`svdPath` launch property.

## Why this is not a Cortex-Debug patch

Cortex-Debug is optimized around GDB and Cortex-M server behavior. C28x requires
TI-specific probe configuration, program loading, word-address conversion and CPU
register definitions. A separate DAP adapter keeps the Arm extension maintainable
while preserving the same VS Code workflow and SVD viewer.

## F28M35x

Two valid workflows are supported:

1. Cortex-Debug for M3 plus a separate C2000 session for C28x;
2. one `c2000-debug` CCS launch that opens both cores as threads.

The second workflow avoids two independent processes fighting over one XDS probe.
