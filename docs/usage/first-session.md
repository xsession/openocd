# First debug session

OpenOCD normally needs at least an adapter configuration and target configuration.

```console
$ openocd -f interface/cmsis-dap.cfg -f target/stm32f4x.cfg
```

Do not start with an empty placeholder configuration. Without an adapter, OpenOCD exits with:

```text
Error: Debug Adapter has to be specified
```

## Connect GDB

In another terminal:

```console
$ arm-none-eabi-gdb firmware.elf
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
(gdb) load
(gdb) continue
```

Default ports:

| Port | Service |
|---:|---|
| 3333 | GDB server |
| 4444 | Telnet command console |
| 6666 | Tcl RPC |

Use `bindto 127.0.0.1` unless remote access is intentionally required.
