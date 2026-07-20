#!/usr/bin/env sh
set -eu

# Convenience defaults for Docker: make OpenOCD reachable from host/LAN.
# Override with OPENOCD_BINDTO=127.0.0.1 if you only want loopback binding.
: "${OPENOCD_BINDTO:=0.0.0.0}"
: "${OPENOCD_EXTRA_ARGS:=}"

if [ "${1:-}" = "sh" ] || [ "${1:-}" = "bash" ]; then
  exec "$@"
fi

if [ "${1:-}" = "openocd" ]; then
  shift
fi

# If no args or help/version was requested, do not append network settings.
case "${1:-}" in
  ""|"--help"|"-h"|"--version"|"-v")
    exec openocd "$@"
    ;;
esac

# shellcheck disable=SC2086
exec openocd -c "bindto ${OPENOCD_BINDTO}" ${OPENOCD_EXTRA_ARGS} "$@"
