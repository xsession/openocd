group "default" {
  targets = ["openocd"]
}

target "openocd" {
  context = "."
  dockerfile = "docker/Dockerfile"
  tags = ["xsession/openocd:local"]
  platforms = ["linux/amd64", "linux/arm64"]
  args = {
    CONFIGURE_FLAGS = "--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl --disable-werror"
  }
}
