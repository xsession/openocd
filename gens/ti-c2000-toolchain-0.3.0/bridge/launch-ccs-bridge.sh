#!/usr/bin/env sh
set -eu
ccs_root="${1:?usage: launch-ccs-bridge.sh <ccs-root> [bridge.js]}"
bridge="${2:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/ccs-debug-bridge.js}"
exec "$ccs_root/ccs/scripting/run.sh" "$bridge"
