#!/usr/bin/env sh
set -eu

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <openocd> <v2|v3|auto> <target-config> <image> [speed-khz]" >&2
  exit 2
fi

OPENOCD=$1
VERSION=$2
TARGET=$3
IMAGE=$4
SPEED=${5:-1000}

case "$VERSION" in
  v2) INTERFACE=interface/ftdi/xds100v2.cfg ;;
  v3) INTERFACE=interface/ftdi/xds100v3.cfg ;;
  auto) INTERFACE=interface/ftdi/xds100.cfg ;;
  *) echo "Unsupported XDS100 version: $VERSION" >&2; exit 2 ;;
esac

exec "$OPENOCD" \
  -f "$INTERFACE" \
  -f "$TARGET" \
  -c "adapter speed $SPEED" \
  -c "program {$IMAGE} verify reset exit"
