#!/bin/sh
set -eu

root=${1:-/src/openocd}
jimtcl_commit=${JIMTCL_COMMIT:-f160866171457474f7c4d6ccda70f9b77524407e}
libjaylink_commit=${LIBJAYLINK_COMMIT:-0d23921a05d5d427332a142d154c213d0c306eb1}

if [ -f "$root/bootstrap" ]; then
    src=$root
elif [ -f "$root/openocd/bootstrap" ]; then
    src=$root/openocd
else
    echo "ERROR: OpenOCD bootstrap was not found under $root" >&2
    find "$root" -maxdepth 4 -type f -name bootstrap -print >&2 || true
    exit 127
fi

fetch_commit() {
    url=$1
    commit=$2
    destination=$3
    rm -rf "$destination"
    git init -q "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch -q --depth 1 origin "$commit"
    git -C "$destination" checkout -q --detach FETCH_HEAD
}

if [ ! -f "$src/jimtcl/autogen.sh" ]; then
    echo "Fetching OpenOCD-pinned Jim Tcl commit $jimtcl_commit" >&2
    fetch_commit https://github.com/msteveb/jimtcl.git "$jimtcl_commit" "$src/jimtcl"
fi

if [ ! -f "$src/src/jtag/drivers/libjaylink/autogen.sh" ]; then
    echo "Fetching OpenOCD-pinned libjaylink commit $libjaylink_commit" >&2
    fetch_commit https://gitlab.zapb.de/libjaylink/libjaylink.git "$libjaylink_commit" "$src/src/jtag/drivers/libjaylink" || \
    fetch_commit https://github.com/damienhackett-eaton/libjaylink.git "$libjaylink_commit" "$src/src/jtag/drivers/libjaylink"
fi

find "$src" -type f \( \
    -name bootstrap -o -name autogen.sh -o -name configure.ac -o \
    -name 'Makefile.am' -o -name '*.m4' -o -name '*.ac' -o \
    -name '*.am' -o -name '*.sh' \
\) -exec sed -i 's/\r$//' {} +
find "$src" -type f \( -name bootstrap -o -name autogen.sh -o -name '*.sh' \) -exec chmod +x {} +

printf '%s\n' "$src"
