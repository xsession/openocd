# TI MSPM0C1103

`target/ti/mspm0c1103.cfg` is a thin device wrapper around OpenOCD's generic
`target/ti/mspm0.cfg` support.

The MSPM0C1103 has a Cortex-M0+ CPU, 8 KiB of flash and 1 KiB of SRAM. The
wrapper limits the OpenOCD work area to the available 1 KiB SRAM. Flash
geometry is not hard-coded because the existing MSPM0 driver reads the device
and factory information registers at probe time.

## Supported probes

Two convenience board configurations are provided:

- `board/ti/mspm0c1103-xds110.cfg`
- `board/ti/mspm0c1103-cmsis-dap.cfg`

Both start at 1 MHz SWD. Increase speed only after the target is stable.

## Smoke test

```text
openocd -f board/ti/mspm0c1103-xds110.cfg \
  -c init \
  -c "reset halt" \
  -c "flash probe 0" \
  -c "flash info 0" \
  -c shutdown
```

Expected minimum result: Cortex-M0+ identification, a successful halt, and an
8 KiB main-flash bank reported by the MSPM0 flash driver.
