# syntax=docker/dockerfile:1.7
# Build a redistributable OpenOCD Linux package.

ARG ALPINE_VERSION=3.20
FROM alpine:${ALPINE_VERSION} AS build

ARG TARGETARCH
ARG JOBS=0
ARG OPENOCD_PREFIX=/opt/openocd
ARG CONFIGURE_FLAGS="--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl"
ARG JIMTCL_COMMIT=f160866171457474f7c4d6ccda70f9b77524407e
ARG LIBJAYLINK_COMMIT=0d23921a05d5d427332a142d154c213d0c306eb1

RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add --no-cache \
      autoconf automake bash ca-certificates coreutils file gcc g++ git \
      hidapi-dev libcap-dev libftdi1-dev libgpiod-dev libjaylink-dev \
      libtool libusb-dev linux-headers make musl-dev pkgconf tar texinfo xz zlib-dev

RUN printf '%s\n' \
      '#!/bin/sh' \
      'if [ -z "${JOBS:-}" ] || [ "${JOBS}" = "0" ]; then' \
      '  nproc' \
      'else' \
      '  printf "%s\\n" "${JOBS}"' \
      'fi' \
      > /usr/local/bin/docker-jobs \
    && chmod +x /usr/local/bin/docker-jobs

ENV JIMTCL_COMMIT=${JIMTCL_COMMIT} \
    LIBJAYLINK_COMMIT=${LIBJAYLINK_COMMIT}

WORKDIR /src/openocd
COPY . .
COPY build/scripts/prepare-openocd-source.sh /usr/local/bin/prepare-openocd-source
RUN chmod +x /usr/local/bin/prepare-openocd-source

RUN set -eux; \
    src="$(prepare-openocd-source /src/openocd)"; \
    cd "${src}"; \
    sh ./bootstrap; \
    ./configure --prefix="${OPENOCD_PREFIX}" ${CONFIGURE_FLAGS} --disable-werror; \
    make -j"$(docker-jobs)"; \
    make install; \
    "${OPENOCD_PREFIX}/bin/openocd" --version; \
    arch="${TARGETARCH:-$(uname -m)}"; \
    case "${arch}" in \
      amd64|x86_64) pkgarch=x86_64 ;; \
      arm64|aarch64) pkgarch=aarch64 ;; \
      *) pkgarch="${arch}" ;; \
    esac; \
    pkg="openocd-linux-${pkgarch}"; \
    mkdir -p "/out/${pkg}"; \
    cp -a "${OPENOCD_PREFIX}/bin" "${OPENOCD_PREFIX}/share" "/out/${pkg}/"; \
    cp -a README* COPYING* LICENSE* "/out/${pkg}/" 2>/dev/null || true; \
    printf '%s\n' \
      '#!/bin/sh' \
      'HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)' \
      'exec "$HERE/bin/openocd" "$@"' \
      > "/out/${pkg}/openocd.sh"; \
    chmod +x "/out/${pkg}/openocd.sh"; \
    cd /out; \
    tar -czf "${pkg}.tar.gz" "${pkg}"

FROM alpine:${ALPINE_VERSION} AS package
COPY --from=build /out/ /out/
VOLUME ["/dist"]
CMD ["/bin/sh", "-c", "set -eu; mkdir -p /dist; cp -a /out/. /dist/; find /dist -maxdepth 3 -type f | sort"]

FROM scratch AS export
COPY --from=build /out/ /
