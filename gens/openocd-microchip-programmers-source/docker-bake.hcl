group "default" {
  targets = ["openocd"]
}

target "openocd" {
  context = "."
  dockerfile = "deploy/docker/Dockerfile"
  tags = ["xsession/openocd:local"]
  platforms = ["linux/amd64", "linux/arm64"]
}
