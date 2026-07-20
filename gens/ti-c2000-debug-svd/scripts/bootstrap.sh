#!/usr/bin/env sh
set -eu
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
ti-svd list
printf '%s\n' 'Environment ready. Run: ti-svd discover --ccs-root /path/to/ti'
