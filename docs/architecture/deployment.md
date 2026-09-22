# C4 deployment view

OpenOCD has one runtime architecture but several supported deployment shapes.
The binary, installed Tcl scripts, and physical hardware must remain aligned;
most failures that look like protocol problems are actually package-path,
permission, or container/USB-boundary problems.

```mermaid
C4Deployment
  title OpenOCD deployment options

  Deployment_Node(workstation, "Developer workstation", "Windows, Linux, or macOS") {
    Container_Instance(native, "OpenOCD executable", "native binary", "Built by Autotools or installed from a package")
    Container_Instance(scripts, "OpenOCD scripts", "pkgdata", "Installed tcl/ scripts, site overrides, SVD and support data")
    Container_Instance(client, "Debugger client", "GDB / IDE", "GDB, VS Code/Cortex-Debug, or Telnet/Tcl client")
  }
  Deployment_Node(container_host, "Container host", "Docker Desktop or Linux host") {
    Container_Instance(openocd_container, "OpenOCD container", "Docker image", "docker/Dockerfile runtime image")
    Container_Instance(usb_device, "USB device boundary", "host device mapping", "USB/JTAG probe passed to container")
  }
  Deployment_Node(board, "Hardware bench", "debug probe and target board") {
    Container_Instance(probe, "Debug adapter", "USB/TCP/GPIO")
    Container_Instance(target, "Target board", "MCU/FPGA/CPLD")
  }

  Rel(client, native, "GDB RSP / Telnet / Tcl")
  Rel(native, scripts, "loads runtime configuration")
  Rel(native, probe, "USB/TCP/GPIO")
  Rel(openocd_container, usb_device, "host USB access")
  Rel(usb_device, probe, "device passthrough")
  Rel(openocd_container, target, "debug/program through probe")
  Rel(probe, target, "JTAG/SWD/SWIM/vendor link")
```

## Deployment shapes

| Shape | Source path | Best for | Important boundary |
|---|---|---|---|
| Native developer build | `./bootstrap`, `./configure`, `make`, `make install` | Local development, hardware bring-up, and fastest iteration. | The executable must find the matching `tcl/` installation or `OPENOCD_SCRIPTS`. |
| Linux package | `docker/Dockerfile.linux-package` | Reproducible Linux archives for amd64/arm64. | Buildx platform and QEMU/binfmt support must match the requested architecture. |
| Windows package | `docker/Dockerfile.windows-cross` | Portable Windows ZIP with drivers and helper tools. | MinGW dependencies and USB driver payloads are built in separate stages. |
| Runtime image | `docker/Dockerfile` | CI, remote runners, and repeatable service execution. | USB access, network ports, and `/work` image paths must be configured by the host. |
| macOS package | `docker/scripts/build-macos-package.sh` | Native macOS x86_64/arm64 packages. | Dependencies are installed with Homebrew on the selected runner. |
| Remote debug service | Native or Docker deployment | A local IDE controlling a probe on another host. | Expose only the intended GDB/Telnet/Tcl ports and secure the network path. |

## Installed paths and script discovery

The build defines `PKGDATADIR` and installs Tcl runtime files under the
OpenOCD package data directory through the `install-data-hook` in `Makefile.am`.
At runtime, `src/helper/options.c` adds search paths in this order:

1. `OPENOCD_SCRIPTS`, when explicitly set;
2. user configuration directories (`APPDATA`, `XDG_CONFIG_HOME`, `~/.config/openocd`, or `~/.openocd`);
3. the package `site` directory;
4. the package `scripts` directory.

The built-in package path is intentionally last so users can override scripts
without modifying the installed package. This is why a deployment guide must
always show both the OpenOCD executable path and the script path.

## Container and USB checklist

- Use the Docker Linux container engine on Docker Desktop when building the
  Alpine-based Linux/Windows images.
- Pass the probe's USB device into the container and verify permissions before
  debugging target configuration.
- Publish only the ports required by the client: normally `3333`, `4444`, and
  `6666`.
- Mount firmware and configuration files into `/work` or provide absolute paths
  visible from the container.
- Keep the runtime image's `/opt/openocd/bin` and
  `/opt/openocd/share/openocd/scripts` together.

See [Docker packaging](../deployment/docker-packaging.md), [CI](../deployment/ci.md),
and [troubleshooting](../deployment/troubleshooting.md) for operational steps.
