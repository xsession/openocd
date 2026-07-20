# Address representation

VS Code SVD viewers ultimately issue byte-addressed memory requests through the
Debug Adapter Protocol. Arm-based MSPM0 and the Cortex-M3 side of Concerto already
use byte addresses, so their manifests use `address_scale = 1` and
`addressUnitBits = 8`.

C28x linker and target metadata commonly express locations in 16-bit addressable
words. The C28x manifests use `address_scale = 2`; peripheral base addresses and
register offsets read from TI target XML are converted to byte addresses in the
viewer-oriented SVD output.

This representation is intended for generic SVD viewers. A C28x debug adapter that
publishes native word addresses instead of byte addresses may require an adapter-side
translation or a separately generated native-address variant. The generated
`vendorExtensions` records the applied scale.

Do not silently change the scale. After changing CCS versions or XML sources,
compare representative peripheral bases against the device technical reference
manual and verify live reads against the CCS memory/register view.
