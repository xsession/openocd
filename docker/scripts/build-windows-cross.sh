#!/usr/bin/env sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OUT_DIR=${OUT_DIR:-"${ROOT_DIR}/artifacts/windows"}
JOBS=${JOBS:-0}
CONFIGURE_FLAGS=${CONFIGURE_FLAGS:---enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-libjaylink --enable-jimtcl-maintainer --enable-internal-jimtcl}
mkdir -p "${OUT_DIR}"
cd "${ROOT_DIR}"
docker buildx build \
  --platform linux/amd64 \
  -f docker/Dockerfile.windows-cross \
  --build-arg "JOBS=${JOBS}" \
  --build-arg "CONFIGURE_FLAGS=${CONFIGURE_FLAGS}" \
  --target export \
  --output "type=local,dest=${OUT_DIR}" \
  .
find "${OUT_DIR}" -maxdepth 3 -type f -print
