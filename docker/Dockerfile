# syntax=docker/dockerfile:1.7
# Build OpenOCD from the current repository checkout.
# Intended usage from repo root:
#   docker build -f docker/Dockerfile -t xsession/openocd:local .

ARG ALPINE_VERSION=3.20
FROM alpine:${ALPINE_VERSION} AS build

# Keep Werror off for deploy builds. This fork currently emits warnings with newer GCC
# such as unsupported/Clang-only warning toggles and local C2000 driver warnings; those
# should not make release container builds fail.
ARG CONFIGURE_FLAGS="--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl"

RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    set -eux; \
    apk add --update-cache --no-progress \
      autoconf \
      automake \
      bash \
      ca-certificates \
      gcc \
      g++ \
      git \
      hidapi-dev \
      libcap-dev \
      libftdi1-dev \
      libgpiod-dev \
      libjaylink-dev \
      libtool \
      libusb-dev \
      linux-headers \
      make \
      musl-dev \
      pkgconf \
      texinfo \
      eudev-dev

WORKDIR /src/openocd
COPY . .

RUN set -eux; \
    ./bootstrap; \
    ./configure --prefix=/opt/openocd ${CONFIGURE_FLAGS} --disable-werror; \
    make -j"$(nproc)"; \
    make install; \
    /opt/openocd/bin/openocd --version

FROM alpine:${ALPINE_VERSION} AS runtime

LABEL org.opencontainers.image.title="xsession-openocd" \
      org.opencontainers.image.description="Docker runtime for xsession/openocd with USB/JTAG access" \
      org.opencontainers.image.source="https://github.com/xsession/openocd"

RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    set -eux; \
    apk add --update-cache --no-progress \
      bash \
      ca-certificates \
      eudev-libs \
      gdb \
      hidapi \
      libcap \
      libftdi1 \
      libgpiod \
      libjaylink \
      libstdc++ \
      libusb \
      tini \
      usbutils

COPY --from=build /opt/openocd /opt/openocd
COPY scripts/openocd-entrypoint.sh /usr/local/bin/openocd-entrypoint.sh
RUN chmod +x /usr/local/bin/openocd-entrypoint.sh

ENV PATH="/opt/openocd/bin:${PATH}" \
    OPENOCD_SCRIPTS="/opt/openocd/share/openocd/scripts"

WORKDIR /work
EXPOSE 3333 4444 6666
ENTRYPOINT ["/sbin/tini","--","/usr/local/bin/openocd-entrypoint.sh"]
CMD ["--help"]
