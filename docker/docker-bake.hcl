group "default" {
  targets = ["linux-amd64", "windows-x86_64"]
}

group "all" {
  targets = ["linux-amd64", "linux-arm64", "windows-x86_64"]
}

variable "JOBS" {
  default = "0"
}

variable "LINUX_CONFIGURE_FLAGS" {
  default = "--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl"
}

variable "WINDOWS_CONFIGURE_FLAGS" {
  default = "--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-internal-libjaylink --enable-jimtcl-maintainer --enable-internal-jimtcl"
}

target "linux-amd64" {
  context = "."
  dockerfile = "docker/Dockerfile.linux-package"
  target = "export"
  platforms = ["linux/amd64"]
  args = {
    JOBS = "${JOBS}"
    CONFIGURE_FLAGS = "${LINUX_CONFIGURE_FLAGS}"
  }
  output = ["type=local,dest=artifacts/linux/amd64"]
}

target "linux-arm64" {
  inherits = ["linux-amd64"]
  platforms = ["linux/arm64"]
  output = ["type=local,dest=artifacts/linux/arm64"]
}

target "windows-x86_64" {
  context = "."
  dockerfile = "docker/Dockerfile.windows-cross"
  target = "export"
  platforms = ["linux/amd64"]
  args = {
    JOBS = "${JOBS}"
    CONFIGURE_FLAGS = "${WINDOWS_CONFIGURE_FLAGS}"
  }
  output = ["type=local,dest=artifacts/windows"]
}
