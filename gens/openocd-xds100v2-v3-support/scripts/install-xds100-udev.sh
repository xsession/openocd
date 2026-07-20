#!/usr/bin/env sh
set -eu
SRC=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../overlay/udev" && pwd)/99-openocd-xds100.rules}
DST=${2:-/etc/udev/rules.d/99-openocd-xds100.rules}
install -m 0644 "$SRC" "$DST"
udevadm control --reload-rules
udevadm trigger
printf 'Installed %s; reconnect the XDS100 probe.\n' "$DST"
