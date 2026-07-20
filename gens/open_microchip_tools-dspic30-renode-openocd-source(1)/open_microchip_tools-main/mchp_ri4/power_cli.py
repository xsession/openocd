from __future__ import annotations

import argparse
import json
from typing import Iterable, Optional

from interfaces.ICD4.icd4_drv import ICD4Driver, ICD4UsbIds
from interfaces.PK4.pk4_drv import PK4Driver, PK4UsbIds


def _discover_pid(vid: int) -> int:
    try:
        import usb.core  # type: ignore
        import usb.backend.libusb1  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyUSB is required for auto-detect; install project extra 'usb'.") from exc

    backend = usb.backend.libusb1.get_backend()
    if backend is None:
        try:
            import libusb_package  # type: ignore
        except Exception:
            libusb_package = None  # type: ignore
        if libusb_package is not None:
            backend = libusb_package.get_libusb1_backend()
    if backend is None:
        raise RuntimeError("PyUSB libusb backend not available; install a libusb-1.0 backend such as 'libusb-package'.")

    devices = list(usb.core.find(find_all=True, idVendor=vid, backend=backend) or [])
    if not devices:
        raise RuntimeError(f"No USB devices found for vid=0x{vid:04X}")
    products = sorted({int(device.idProduct) for device in devices})
    if len(products) != 1:
        rendered = ", ".join(f"0x{product:04X}" for product in products)
        raise RuntimeError(f"Multiple USB product IDs found for vid=0x{vid:04X}: {rendered}. Re-run with --pid.")
    return products[0]


def _open_driver(tool: str, vid: int, pid: int):
    normalized = tool.strip().lower()
    if normalized == "pk4":
        return PK4Driver(PK4UsbIds(vid=vid, pid=pid))
    if normalized == "icd4":
        return ICD4Driver(ICD4UsbIds(vid=vid, pid=pid))
    raise RuntimeError(f"Unsupported tool: {tool}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Drive target power from a PICkit 4/ICD4 over the repo-local RI4 transport")
    parser.add_argument("--tool", choices=("pk4", "icd4"), default="pk4")
    parser.add_argument("--vid", default="0x04D8")
    parser.add_argument("--pid", default="")
    parser.add_argument("--voltage", type=float, default=5.0, help="Requested target voltage in volts")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--power-off", action="store_true")
    parser.add_argument("--no-maintain-active", action="store_true")
    parser.add_argument("--no-live-connect", action="store_true")
    parser.add_argument("--high-voltage-programming", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    vid = int(str(args.vid), 0)
    pid = int(str(args.pid), 0) if str(args.pid).strip() else _discover_pid(vid)
    voltage_mv = int(round(float(args.voltage) * 1000.0))

    driver = _open_driver(str(args.tool), vid, pid)
    try:
        if args.status_only:
            result = {"tool": str(args.tool).upper(), "vid": f"0x{vid:04X}", "pid": f"0x{pid:04X}", "status": driver.power_status()}
        elif args.power_off:
            result = {"tool": str(args.tool).upper(), "vid": f"0x{vid:04X}", "pid": f"0x{pid:04X}", **driver.shutdown_power()}
        else:
            result = {
                "tool": str(args.tool).upper(),
                "vid": f"0x{vid:04X}",
                "pid": f"0x{pid:04X}",
                **driver.power_target(
                    voltage_mv,
                    from_tool=True,
                    maintain_active=not bool(args.no_maintain_active),
                    live_connect=not bool(args.no_live_connect),
                    use_low_voltage_programming=not bool(args.high_voltage_programming),
                ),
            }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())