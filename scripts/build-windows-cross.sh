#!/usr/bin/env sh
set -eu

OUT_DIR="${OUT_DIR:-docker/data/dist/windows}"
IMAGE_BUILDER="${IMAGE_BUILDER:-xsession/openocd:windows-cross-builder}"
CONFIGURE_FLAGS="${CONFIGURE_FLAGS:---enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-jimtcl}"

mkdir -p "${OUT_DIR}"

docker buildx build \
  -f docker/Dockerfile.windows-cross \
  --build-arg CONFIGURE_FLAGS="${CONFIGURE_FLAGS}" \
  --target export \
  --output "type=local,dest=${OUT_DIR}" \
  -t "${IMAGE_BUILDER}" \
  .

printf 'Windows package written to %s\n' "${OUT_DIR}"
ls -la "${OUT_DIR}"
