#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu

ARCH="${LIBWDI_ARCH:-x64}"
SOURCE_DIR="${SOURCE_DIR:-/src/libwdi}"
OUTPUT_DIR="${OUTPUT_DIR:-/out}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '2')}"

case "$ARCH" in
  x64)
    HOST=x86_64-w64-mingw32
    ARCH_OPTION=--disable-32bit
    ;;
  x86)
    HOST=i686-w64-mingw32
    ARCH_OPTION=--disable-64bit
    ;;
  *)
    echo "LIBWDI_ARCH must be x86 or x64 (got: $ARCH)" >&2
    exit 2
    ;;
esac

BUILD_ROOT="/work/${ARCH}"
STAGE_ROOT="${BUILD_ROOT}/stage"
PACKAGE_ROOT="${BUILD_ROOT}/package/libwdi-${ARCH}"
WDK_DIR="/opt/libwdi-input/wdk/Program Files/Windows Kits/8.0"

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/source" "$STAGE_ROOT" "$PACKAGE_ROOT" "$OUTPUT_DIR"

tar -C "$SOURCE_DIR" \
  --exclude=.git --exclude=dist --exclude=docker \
  -cf - . | tar -C "$BUILD_ROOT/source" -xf -

cd "$BUILD_ROOT/source"

./bootstrap.sh
./configure \
  --build="$(gcc -dumpmachine)" \
  --host="$HOST" \
  "$ARCH_OPTION" \
  --enable-toggable-debug \
  --enable-examples-build \
  --disable-debug \
  --disable-shared \
  --with-wdkdir="$WDK_DIR" \
  --with-wdfver=1011 \
  --with-libusb0=/opt/libwdi-input/libusb0 \
  --with-libusbk=/opt/libwdi-input/libusbk

# libwdi discovers these values only for native MinGW builds. The Docker image
# uses the fixed WDK 8 redistributable layout, so define them for cross builds.
printf '%s\n' \
  '#define COINSTALLER_DIR "wdf"' \
  '#define X64_DIR "x64"' >> config.h

make -j"$JOBS"
make DESTDIR="$STAGE_ROOT" install

mkdir -p "$PACKAGE_ROOT/bin" "$PACKAGE_ROOT/include" "$PACKAGE_ROOT/lib/pkgconfig"
cp examples/zadig.exe examples/wdi-simple.exe "$PACKAGE_ROOT/bin/"
cp "$STAGE_ROOT/usr/local/include/libwdi.h" "$PACKAGE_ROOT/include/"
cp "$STAGE_ROOT/usr/local/lib/libwdi.a" "$PACKAGE_ROOT/lib/"
cp libwdi/.libs/libwdi.dll.a "$PACKAGE_ROOT/lib/"
cp "$STAGE_ROOT/usr/local/lib/pkgconfig/libwdi.pc" "$PACKAGE_ROOT/lib/pkgconfig/"
cp AUTHORS COPYING COPYING-LGPL ChangeLog NEWS README.md "$PACKAGE_ROOT/"

VERSION="$(sed -n 's/^AC_INIT(\[libwdi\],\[\([^]]*\)\].*/\1/p' configure.ac)"
ARCHIVE="libwdi-${VERSION}-${ARCH}.zip"
(
  cd "$BUILD_ROOT/package"
  find "libwdi-$ARCH" -type f -print | LC_ALL=C sort | zip -X -q "$OUTPUT_DIR/$ARCHIVE" -@
)
(
  cd "$OUTPUT_DIR"
  sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
)

echo "Created $OUTPUT_DIR/$ARCHIVE"
