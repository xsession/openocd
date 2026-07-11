#!/usr/bin/env sh
set -eu

JOBS=${JOBS:-0}
CONFIGURE_FLAGS=${CONFIGURE_FLAGS:---enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl}

build_one() {
  platform=$1
  arch_dir=$2
  out="docker/data/dist/linux/$arch_dir"
  mkdir -p "$out"
  docker buildx build \
    --platform "$platform" \
    -f docker/Dockerfile.linux-package \
    --build-arg "JOBS=$JOBS" \
    --build-arg "CONFIGURE_FLAGS=$CONFIGURE_FLAGS" \
    --target export \
    --output "type=local,dest=$out" \
    .
}

build_one linux/amd64 amd64
if [ "${BUILD_ARM64:-0}" = "1" ]; then
  build_one linux/arm64 arm64
fi
