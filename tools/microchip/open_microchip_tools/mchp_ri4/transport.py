from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Deque, Dict, Optional
from collections import deque

from .errors import Ri4TransportError


class ToolTransport:
    """Abstract byte transport (USB, TCP, etc.)."""

    def send(self, endpoint: int, data: bytes, timeout_ms: int) -> None:
        raise NotImplementedError

    def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        return None


@dataclass
class _QueuedResponse:
    endpoint: int
    data: bytes


class FakeTransport(ToolTransport):
    """In-memory transport for tests.

    You can install an `on_send` hook to synthesize responses.
    """

    def __init__(self, *, on_send: Optional[Callable[[int, bytes, int], None]] = None):
        self._queues: Dict[int, Deque[bytes]] = {}
        self.on_send = on_send

    def queue_recv(self, endpoint: int, data: bytes) -> None:
        self._queues.setdefault(endpoint, deque()).append(bytes(data))

    def send(self, endpoint: int, data: bytes, timeout_ms: int) -> None:
        if self.on_send is not None:
            self.on_send(endpoint, bytes(data), timeout_ms)

    def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
        q = self._queues.get(endpoint)
        if not q:
            raise Ri4TransportError(f"No queued response for endpoint 0x{endpoint:02x}")
        data = q.popleft()
        if len(data) > length:
            q.appendleft(data[length:])
            return data[:length]
        return data

    def close(self) -> None:
        self._queues.clear()


class PyusbTransport(ToolTransport):
    """Optional PyUSB-backed transport.

    This is intentionally minimal; users must ensure device permissions/drivers.
    """

    def __init__(
        self,
        *,
        vid: int,
        pid: int,
        interface: int = 0,
        serial_number: Optional[str] = None,
        reset_device: bool = False,
    ):
        try:
            import usb.core  # type: ignore
            import usb.backend.libusb1  # type: ignore
            import usb.util  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise Ri4TransportError(
                "PyUSB not available; install extra 'usb' (pyusb)."
            ) from exc

        self._usb = usb  # type: ignore
        backend = usb.backend.libusb1.get_backend()
        if backend is None:
            try:
                import libusb_package  # type: ignore
            except Exception:
                libusb_package = None  # type: ignore
            if libusb_package is not None:
                backend = libusb_package.get_libusb1_backend()
        if backend is None:
            raise Ri4TransportError(
                "PyUSB libusb backend not available; install a libusb-1.0 backend such as 'libusb-package'."
            )

        if serial_number:
            devices = usb.core.find(idVendor=vid, idProduct=pid, backend=backend, find_all=True)
            self._dev = None
            for candidate in devices or ():
                try:
                    candidate_serial = usb.util.get_string(candidate, candidate.iSerialNumber)
                except Exception:
                    candidate_serial = None
                if candidate_serial == serial_number:
                    self._dev = candidate
                    break
        else:
            self._dev = usb.core.find(idVendor=vid, idProduct=pid, backend=backend)
        if self._dev is None:
            suffix = f" serial={serial_number!r}" if serial_number else ""
            raise Ri4TransportError(f"USB device not found vid=0x{vid:04x} pid=0x{pid:04x}{suffix}")

        self._interface = interface
        self._closed = False
        self._known_endpoints = (0x02, 0x81, 0x04, 0x83, 0x03)
        try:
            if self._dev.is_kernel_driver_active(interface):
                self._dev.detach_kernel_driver(interface)
        except Exception:
            pass

        try:
            if reset_device:
                try:
                    self._dev.reset()
                except Exception:
                    pass
            self._dev.set_configuration()
            try:
                self._dev.set_interface_altsetting(interface=interface, alternate_setting=0)
            except Exception:
                pass
            usb.util.claim_interface(self._dev, interface)
            for endpoint in self._known_endpoints:
                try:
                    self._dev.clear_halt(endpoint)
                except Exception:
                    pass
        except Exception as exc:
            raise Ri4TransportError("Failed to claim USB interface") from exc

    def send(self, endpoint: int, data: bytes, timeout_ms: int) -> None:
        try:
            self._dev.write(endpoint, data, timeout=timeout_ms)
        except Exception as exc:
            raise Ri4TransportError(f"USB write failed ep=0x{endpoint:02x}") from exc

    def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
        try:
            res = self._dev.read(endpoint, length, timeout=timeout_ms)
            return bytes(res)
        except Exception as exc:
            raise Ri4TransportError(f"USB read failed ep=0x{endpoint:02x}") from exc

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._usb.util.release_interface(self._dev, self._interface)
        except Exception:
            pass
        try:
            self._usb.util.dispose_resources(self._dev)
        except Exception:
            pass
        self._closed = True
