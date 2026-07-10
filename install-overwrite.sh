#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cp -a "$SCRIPT_DIR/files/." .
printf '%s\n' 'Done. Now run: docker compose up --build'
