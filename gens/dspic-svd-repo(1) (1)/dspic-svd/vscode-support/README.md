# Cortex-Debug dsPIC device support pack

This optional VS Code extension registers generated SVD files for:

- dsPIC30F5011
- dsPIC33FJ128MC802
- dsPIC33FJ128MC804
- dsPIC33EP128GM604

Build it after generating the SVDs:

```bash
make update
make check-generated
make vsix
```

The direct and most predictable configuration is still an explicit SVD path in `launch.json`:

```jsonc
{
  "type": "cortex-debug",
  "request": "attach",
  "servertype": "external",
  "device": "dsPIC33EP128GM604",
  "svdFile": "${workspaceFolder}/svd/dspic33ep128gm604.svd"
}
```

When the installed Cortex-Debug version exposes its device-support-pack API, this extension also maps the exact `device` name to the packaged SVD automatically. If that API is unavailable, Cortex-Debug continues to work with the explicit `svdFile` setting.

This package supplies peripheral metadata only. Program execution, breakpoints, registers, and memory access still require a dsPIC-capable GDB client and GDB remote server. A non-Cortex-Debug dsPIC adapter may instead use the standalone MCU Peripheral Viewer with `svdPath` if it implements Debug Adapter Protocol memory reads.
