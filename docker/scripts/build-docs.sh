#!/usr/bin/env sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OUT_DIR=${OUT_DIR:-"${ROOT_DIR}/docs/_build/export"}
mkdir -p "${OUT_DIR}"
cd "${ROOT_DIR}"
docker buildx build \
  -f docker/Dockerfile.docs \
  --target export \
  --output "type=local,dest=${OUT_DIR}" \
  .
printf 'Documentation exported to %s\n' "${OUT_DIR}"
