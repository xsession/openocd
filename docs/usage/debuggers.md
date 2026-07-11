# Debugger integration

## Command-line GDB

```console
$ arm-none-eabi-gdb build/firmware.elf \
  -ex "target extended-remote localhost:3333"
```

## VS Code

Common extensions can launch OpenOCD or attach to an existing GDB server. Configure:

- the package's `openocd`/`openocd.exe` path;
- the package's `share/openocd/scripts` search path if the extension does not infer it;
- adapter and target configuration files;
- the cross-GDB executable matching the target architecture.

## Remote OpenOCD

Run OpenOCD near the hardware and connect GDB over a trusted network or VPN. Do not expose ports 3333, 4444, or 6666 directly to an untrusted LAN.
