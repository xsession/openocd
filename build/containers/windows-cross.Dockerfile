# syntax=docker/dockerfile:1.7
# Cross-compile OpenOCD for Windows x86_64 and export a portable ZIP.
#
# Direct export:
#   docker buildx build -f build/containers/windows-cross.Dockerfile \
#     --target export --output type=local,dest=artifacts/windows .

ARG ALPINE_VERSION=3.20
FROM alpine:${ALPINE_VERSION} AS build

ARG TARGET=x86_64-w64-mingw32
ARG JOBS=0
ARG OPENOCD_PREFIX=/opt/openocd-win64
ARG CONFIGURE_FLAGS="--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-libjaylink --enable-jimtcl-maintainer --enable-internal-jimtcl"
ARG LIBUSB_VERSION=1.0.27
ARG HIDAPI_VERSION=0.14.0
ARG LIBCONFUSE_VERSION=3.3
ARG LIBFTDI_VERSION=1.5
ARG JIMTCL_COMMIT=f160866171457474f7c4d6ccda70f9b77524407e
ARG LIBJAYLINK_COMMIT=0d23921a05d5d427332a142d154c213d0c306eb1

RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add --no-cache \
      autoconf automake bash bzip2 ca-certificates cmake coreutils curl file \
      gcc g++ git gettext gettext-dev libtool make meson \
      mingw-w64-binutils mingw-w64-crt mingw-w64-gcc mingw-w64-headers \
      ninja patch pkgconf python3 tar texinfo xz zip

RUN printf '%s\n' \
      '#!/bin/sh' \
      'if [ -z "${JOBS:-}" ] || [ "${JOBS}" = "0" ]; then' \
      '  nproc' \
      'else' \
      '  printf "%s\\n" "${JOBS}"' \
      'fi' \
      > /usr/local/bin/docker-jobs \
    && chmod +x /usr/local/bin/docker-jobs

ENV TARGET=${TARGET} \
    PREFIX=${OPENOCD_PREFIX} \
    PATH="/usr/${TARGET}/bin:/usr/bin:${PATH}" \
    PKG_CONFIG_LIBDIR="${OPENOCD_PREFIX}/lib/pkgconfig" \
    PKG_CONFIG_PATH="${OPENOCD_PREFIX}/lib/pkgconfig" \
    CC="${TARGET}-gcc" \
    CXX="${TARGET}-g++" \
    AR="${TARGET}-ar" \
    RANLIB="${TARGET}-ranlib" \
    STRIP="${TARGET}-strip" \
    WINDRES="${TARGET}-windres" \
    JIMTCL_COMMIT=${JIMTCL_COMMIT} \
    LIBJAYLINK_COMMIT=${LIBJAYLINK_COMMIT}

WORKDIR /deps

RUN set -eux; \
    curl --retry 5 --retry-delay 2 --retry-connrefused -fsSL \
      "https://github.com/libusb/libusb/releases/download/v${LIBUSB_VERSION}/libusb-${LIBUSB_VERSION}.tar.bz2" \
      -o libusb.tar.bz2; \
    tar -xf libusb.tar.bz2; \
    cd "libusb-${LIBUSB_VERSION}"; \
    ./configure --host="${TARGET}" --prefix="${PREFIX}" --disable-shared --enable-static; \
    make -j"$(docker-jobs)"; \
    make install

RUN set -eux; \
    git clone --depth 1 --branch "hidapi-${HIDAPI_VERSION}" https://github.com/libusb/hidapi.git; \
    cmake -S hidapi -B hidapi-build -G Ninja \
      -DCMAKE_SYSTEM_NAME=Windows \
      -DCMAKE_C_COMPILER="${TARGET}-gcc" \
      -DCMAKE_RC_COMPILER="${TARGET}-windres" \
      -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF; \
    cmake --build hidapi-build --parallel "$(docker-jobs)"; \
    cmake --install hidapi-build

# libconfuse is needed by libftdi's ftdi_eeprom utility. Build only the
# library subtree because the upstream example programs use Unix-only headers.
RUN set -eux; \
    curl --retry 5 --retry-delay 2 --retry-connrefused -fsSL \
      "https://github.com/libconfuse/libconfuse/releases/download/v${LIBCONFUSE_VERSION}/confuse-${LIBCONFUSE_VERSION}.tar.xz" \
      -o confuse.tar.xz; \
    tar -xf confuse.tar.xz; \
    cd "confuse-${LIBCONFUSE_VERSION}"; \
    ./configure --host="${TARGET}" --prefix="${PREFIX}" --disable-shared --enable-static --disable-nls; \
    make -C src -j"$(docker-jobs)"; \
    make -C src install; \
    install -d "${PREFIX}/lib/pkgconfig"; \
    install -m 0644 libconfuse.pc "${PREFIX}/lib/pkgconfig/libconfuse.pc"

RUN set -eux; \
    curl --retry 5 --retry-delay 2 --retry-connrefused -fsSL \
      "https://www.intra2net.com/en/developer/libftdi/download/libftdi1-${LIBFTDI_VERSION}.tar.bz2" \
      -o libftdi.tar.bz2; \
    tar -xf libftdi.tar.bz2; \
    cmake -S "libftdi1-${LIBFTDI_VERSION}" -B libftdi-build -G Ninja \
      -DCMAKE_SYSTEM_NAME=Windows \
      -DCMAKE_C_COMPILER="${TARGET}-gcc" \
      -DCMAKE_CXX_COMPILER="${TARGET}-g++" \
      -DCMAKE_RC_COMPILER="${TARGET}-windres" \
      -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DFTDIPP=OFF \
      -DFTDI_EEPROM=ON \
      -DEXAMPLES=OFF \
      -DDOCUMENTATION=OFF \
      -DLIBUSB_INCLUDE_DIR="${PREFIX}/include/libusb-1.0" \
      -DLIBUSB_LIBRARIES="${PREFIX}/lib/libusb-1.0.a" \
      -DCONFUSE_INCLUDE_DIR="${PREFIX}/include" \
      -DCONFUSE_LIBRARY="${PREFIX}/lib/libconfuse.a"; \
    cmake --build libftdi-build --parallel "$(docker-jobs)"; \
    cmake --install libftdi-build

WORKDIR /src/openocd
COPY . .
COPY build/scripts/prepare-openocd-source.sh /usr/local/bin/prepare-openocd-source
COPY build/scripts/patch-jimtcl-mingw-aio.py /usr/local/bin/patch-jimtcl-mingw-aio
RUN chmod +x /usr/local/bin/prepare-openocd-source /usr/local/bin/patch-jimtcl-mingw-aio

RUN set -eux; \
    src="$(prepare-openocd-source /src/openocd)"; \
    cd "${src}"; \
    patch-jimtcl-mingw-aio jimtcl; \
    sh ./bootstrap; \
    ./configure \
      --host="${TARGET}" \
      --build="$(gcc -dumpmachine)" \
      --prefix="${PREFIX}" \
      PKG_CONFIG_LIBDIR="${PKG_CONFIG_LIBDIR}" \
      CFLAGS="-O2 -I${PREFIX}/include -I${PREFIX}/include/libusb-1.0" \
      LDFLAGS="-L${PREFIX}/lib -static -static-libgcc" \
      LIBS="-lws2_32 -lsetupapi -lole32 -luuid" \
      ${CONFIGURE_FLAGS} \
      --disable-werror; \
    make -j"$(docker-jobs)"; \
    make install; \
    "${STRIP}" "${PREFIX}/bin/openocd.exe" || true; \
    "${STRIP}" "${PREFIX}/bin/ftdi_eeprom.exe" || true; \
    pkg=openocd-windows-x86_64; \
    mkdir -p "/out/${pkg}"; \
    cp -a "${PREFIX}/bin" "${PREFIX}/share" "/out/${pkg}/"; \
    cp -a README* COPYING* LICENSE* "/out/${pkg}/" 2>/dev/null || true; \
    printf '@echo off\r\n%%~dp0bin\\openocd.exe %%*\r\n' > "/out/${pkg}/openocd.cmd"; \
    cd /out; \
    zip -r "${pkg}.zip" "${pkg}"

FROM alpine:${ALPINE_VERSION} AS package
COPY --from=build /out/ /out/
VOLUME ["/dist"]
CMD ["/bin/sh", "-c", "set -eu; mkdir -p /dist; cp -a /out/. /dist/; find /dist -maxdepth 3 -type f | sort"]

FROM scratch AS export
COPY --from=build /out/ /
