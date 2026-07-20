#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHONPATH=src python3 -m unittest discover -s tests -v
(
  cd extension
  npm test
)
./openocd/tests/run.sh
