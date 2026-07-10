group "default" {
  # Default is safe on ordinary Windows/amd64 Docker Desktop installs.
  # It does not require ARM64 emulation.
  targets = ["linux-amd64", "windows-x86_64"]
}

group "all" {
  # Full Docker-supported set. linux-arm64 requires QEMU/binfmt on non-arm64 hosts.
  targets = ["linux-amd64", "linux-arm64", "windows-x86_64"]
}

group "linux" {
  targets = ["linux-amd64"]
}

group "linux-all" {
  targets = ["linux-amd64", "linux-arm64"]
}

variable "CONFIGURE_FLAGS" {
  default = "--enable-ftdi --enable-stlink --enable-cmsis-dap --enable-jlink --enable-jimtcl-maintainer --enable-internal-jimtcl"
}

variable "JOBS" {
  default = "0"
}

target "linux-amd64" {
  context = "."
  dockerfile = "docker/Dockerfile.linux-package"
  target = "export"
  platforms = ["linux/amd64"]
  output = ["type=local,dest=docker/data/dist/linux/amd64"]
  args = {
    CONFIGURE_FLAGS = CONFIGURE_FLAGS
    JOBS = JOBS
  }
}

target "linux-arm64" {
  context = "."
  dockerfile = "docker/Dockerfile.linux-package"
  target = "export"
  platforms = ["linux/arm64"]
  output = ["type=local,dest=docker/data/dist/linux/arm64"]
  args = {
    CONFIGURE_FLAGS = CONFIGURE_FLAGS
    JOBS = JOBS
  }
}

target "windows-x86_64" {
  context = "."
  dockerfile = "docker/Dockerfile.windows-cross"
  target = "export"
  output = ["type=local,dest=docker/data/dist/windows"]
  args = {
    CONFIGURE_FLAGS = CONFIGURE_FLAGS
    JOBS = JOBS
  }
}
