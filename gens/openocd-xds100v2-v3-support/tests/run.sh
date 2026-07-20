#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
tclsh "$ROOT/tests/test_xds100_configs.tcl"
python3 "$ROOT/scripts/validate_bundle.py" "$ROOT"
