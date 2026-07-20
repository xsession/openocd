#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUT_DIR=${OUT_DIR:-"${ROOT_DIR}/artifacts/macos"}
PREFIX=${PREFIX:-"${ROOT_DIR}/.build/macos/install"}
JOBS=${JOBS:-$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)}
CONFIGURE_FLAGS=${CONFIGURE_FLAGS:-"--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl"}

mkdir -p "${OUT_DIR}" "${PREFIX}"
cd "${ROOT_DIR}"

docker/scripts/prepare-openocd-source.sh "${ROOT_DIR}" >/dev/null
sh ./bootstrap
./configure --prefix="${PREFIX}" ${CONFIGURE_FLAGS} --disable-werror
make -j"${JOBS}"
make install

arch=$(uname -m)
case "${arch}" in
  x86_64) pkgarch=x86_64 ;;
  arm64) pkgarch=arm64 ;;
  *) pkgarch=${arch} ;;
esac
pkg="openocd-macos-${pkgarch}"
stage=$(mktemp -d)
trap 'rm -rf "${stage}"' EXIT
mkdir -p "${stage}/${pkg}"
cp -a "${PREFIX}/bin" "${PREFIX}/share" "${stage}/${pkg}/"
cp -a README* COPYING* LICENSE* "${stage}/${pkg}/" 2>/dev/null || true
(
  cd "${stage}"
  tar -czf "${OUT_DIR}/${pkg}.tar.gz" "${pkg}"
)
