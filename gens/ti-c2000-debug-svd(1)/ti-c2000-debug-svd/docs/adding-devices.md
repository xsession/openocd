# Adding another TI device

1. Copy the closest manifest in `devices/`.
2. Set the exact device name and prioritized CCS XML filename patterns.
3. Set `address_scale = 2` for C28x word-address metadata or `1` for byte-addressed cores.
4. Set `cortex_debug = true` only for an Arm Cortex-M target that can be represented by Cortex-Debug.
5. Set `processor_name` to the SVD/viewer processor identity, such as `cm0plus`, `cm3`, or `c28x`.
6. Run `ti-svd discover --device <id> --ccs-root <path>`.
7. Generate with an explicit `--device-xml` the first time.
8. Add deterministic corrections to `patches/<id>.json`; do not edit generated XML by hand.
9. Run `ti-svd validate` and the unit tests.
10. Verify register bases and representative fields against the TI technical reference manual and live hardware.

The validator automatically applies the strict Cortex-Debug profile to manifests
marked `cortex_debug = true`. Do not use that flag merely because an SVD viewer can
open the file; CPU architecture support and SVD parsing are separate concerns.
