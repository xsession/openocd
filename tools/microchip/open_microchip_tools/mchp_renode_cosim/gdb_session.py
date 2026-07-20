from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from mchp_gdbrsp import GdbRemoteClient, StopReply
from mchp_simulator.firmware_image import FirmwareImage


class RenodeSessionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenodeCoreProfile:
    name: str
    pc_register: int
    pc_bytes: int
    flash_base: int
    flash_size: int
    reset_pc: int = 0
    image_address_bias: int = 0


_CORE_PROFILES: Tuple[Tuple[str, RenodeCoreProfile], ...] = (
    (
        "DSPIC30",
        RenodeCoreProfile(
            name="dsPIC30",
            pc_register=16,
            pc_bytes=4,
            flash_base=0x100000,
            flash_size=0x00AC00,
            image_address_bias=0x100000,
        ),
    ),
    (
        "DSPIC33",
        RenodeCoreProfile(
            name="dsPIC33",
            pc_register=16,
            pc_bytes=4,
            flash_base=0x000000,
            flash_size=0x040000,
        ),
    ),
    (
        "PIC18",
        RenodeCoreProfile(
            name="PIC18",
            pc_register=3,
            pc_bytes=4,
            flash_base=0x000000,
            flash_size=0x020000,
        ),
    ),
    (
        "PIC16",
        RenodeCoreProfile(
            name="PIC16",
            pc_register=1,
            pc_bytes=2,
            flash_base=0x000000,
            flash_size=0x004000,
        ),
    ),
)


def profile_for_core(processor: str, family: Optional[str] = None) -> RenodeCoreProfile:
    key = f"{family or ''} {processor}".upper()
    for marker, profile in _CORE_PROFILES:
        if marker in key:
            return profile
    return RenodeCoreProfile(
        name=(family or processor or "generic"),
        pc_register=0,
        pc_bytes=4,
        flash_base=0,
        flash_size=0x10000,
    )


@dataclass
class RenodeGdbSession:
    """OpenOCD bridge backend backed by Renode's GDB server.

    Its public operations deliberately mirror ``NamedScriptSession`` so the
    existing newline-JSON bridge and OpenOCD target driver can use a real PK4 or
    an emulated Renode target without changing the target-facing protocol.
    """

    client: GdbRemoteClient
    processor: str
    family: Optional[str] = None
    pc_register: int = 0
    pc_bytes: int = 4
    flash_base: int = 0
    flash_size: int = 0x10000
    reset_pc: int = 0
    image_address_bias: int = 0
    transfer_chunk_size: int = 1024
    tool: str = "RENODE"
    _debug_state: str = field(default="halted", init=False, repr=False)
    _last_stop: Optional[StopReply] = field(default=None, init=False, repr=False)
    _run_error: Optional[BaseException] = field(default=None, init=False, repr=False)
    _run_thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _run_stopped: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _state_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _hardware_slots: Dict[int, Dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _supported: Dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _start_output: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        if self.pc_register < 0:
            raise ValueError("pc_register must be non-negative")
        if self.pc_bytes <= 0:
            raise ValueError("pc_bytes must be positive")
        if self.flash_base < 0 or self.flash_size <= 0:
            raise ValueError("flash range must be non-negative and non-empty")
        if self.image_address_bias < 0:
            raise ValueError("image_address_bias must be non-negative")
        if self.transfer_chunk_size <= 0:
            raise ValueError("transfer_chunk_size must be positive")
        self.family = self.family.strip().upper() if self.family else None
        self._run_stopped.set()

    @classmethod
    def open_gdb(
        cls,
        *,
        host: str,
        port: int,
        processor: str,
        family: Optional[str] = None,
        timeout: float = 3.0,
        pc_register: Optional[int] = None,
        pc_bytes: Optional[int] = None,
        flash_base: Optional[int] = None,
        flash_size: Optional[int] = None,
        reset_pc: Optional[int] = None,
        image_address_bias: Optional[int] = None,
        transfer_chunk_size: int = 1024,
    ) -> "RenodeGdbSession":
        profile = profile_for_core(processor, family)
        client = GdbRemoteClient(host=host, port=port, timeout=timeout, try_no_ack=True)
        supported = client.connect()
        session = cls(
            client=client,
            processor=processor,
            family=family,
            pc_register=profile.pc_register if pc_register is None else pc_register,
            pc_bytes=profile.pc_bytes if pc_bytes is None else pc_bytes,
            flash_base=profile.flash_base if flash_base is None else flash_base,
            flash_size=profile.flash_size if flash_size is None else flash_size,
            reset_pc=profile.reset_pc if reset_pc is None else reset_pc,
            image_address_bias=(
                profile.image_address_bias if image_address_bias is None else image_address_bias
            ),
            transfer_chunk_size=transfer_chunk_size,
        )
        session._supported = supported
        try:
            session._last_stop = client.query_stop()
        except Exception:
            # Some GDB servers do not implement '?'; an attached Renode target is
            # still initially controlled as halted by the bridge.
            session._last_stop = None
        try:
            # Renode deliberately separates CPU continue from global virtual-time
            # flow. Starting the emulation through qRcmd keeps step/continue usable
            # even when StartGdbServer was created without autostartEmulation.
            session._start_output = client.remote_command("start")
        except Exception as exc:
            client.close()
            raise RenodeSessionError(f"Unable to start Renode emulation through GDB monitor: {exc}") from exc
        return session

    @property
    def endpoint(self) -> str:
        return f"{self.client.host}:{self.client.port}"

    def script_inventory(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "backend": "renode-gdb",
            "processor": self.processor,
            "family": self.family,
            "endpoint": self.endpoint,
            "pcRegister": self.pc_register,
            "pcBytes": self.pc_bytes,
            "flashBase": self.flash_base,
            "flashSize": self.flash_size,
            "imageAddressBias": self.image_address_bias,
            "debugState": self._debug_state,
            "lastStop": None if self._last_stop is None else self._stop_dict(self._last_stop),
            "gdbFeatures": dict(self._supported),
            "startOutput": self._start_output,
            "capabilities": self.capabilities(),
        }

    def capabilities(self) -> Dict[str, bool]:
        return {
            "flash": True,
            "erase": True,
            "verify": True,
            "debug": True,
            "poll": True,
            "setPc": True,
            "breakpoints": True,
            "watchpoints": True,
            "reset": True,
            "programRead": True,
            "programWrite": True,
            "memoryRead": True,
            "memoryWrite": True,
        }

    def close(self) -> None:
        try:
            if self._debug_state == "running":
                try:
                    self.halt_target()
                except Exception:
                    pass
        finally:
            self.client.close()
            with self._state_lock:
                self._debug_state = "unknown"

    def enter_debug_mode(self) -> Dict[str, Any]:
        if self._debug_state == "running":
            self.halt_target()
        with self._state_lock:
            self._debug_state = "halted"
        return {"backend": "renode-gdb", "state": "halted", "endpoint": self.endpoint}

    def exit_debug_mode(self) -> Dict[str, Any]:
        if self._debug_state == "running":
            self.halt_target()
        return {"backend": "renode-gdb", "state": self._debug_state}

    def get_pc(self) -> Dict[str, Any]:
        self._require_halted()
        raw = self.client.read_register(self.pc_register)
        normalized = raw[: self.pc_bytes].ljust(self.pc_bytes, b"\x00")
        return {"pc": int.from_bytes(normalized, "little"), "rawHex": normalized.hex()}

    def set_pc(self, address: int) -> Dict[str, Any]:
        self._require_halted()
        if address < 0 or address >= (1 << (8 * self.pc_bytes)):
            raise ValueError(f"PC value 0x{address:X} does not fit in {self.pc_bytes} bytes")
        raw = address.to_bytes(self.pc_bytes, "little")
        self.client.write_register(self.pc_register, raw)
        return {"pc": address, "rawHex": raw.hex(), "register": self.pc_register}

    def run_target(self) -> Dict[str, Any]:
        with self._state_lock:
            if self._debug_state == "running":
                return {"state": "running", "alreadyRunning": True}
            self._run_error = None
            self._last_stop = None
            self._debug_state = "running"
            self._run_stopped.clear()
            self._run_thread = threading.Thread(
                target=self._continue_worker,
                name="renode-gdb-continue",
                daemon=True,
            )
            self._run_thread.start()
        return {"state": "running", "endpoint": self.endpoint}

    def _continue_worker(self) -> None:
        try:
            stop = self.client.continue_exec()
            with self._state_lock:
                self._last_stop = stop
                self._debug_state = "halted"
        except BaseException as exc:
            with self._state_lock:
                self._run_error = exc
                self._debug_state = "unknown"
        finally:
            self._run_stopped.set()

    def halt_target(self) -> Dict[str, Any]:
        with self._state_lock:
            state = self._debug_state
        if state == "halted":
            return {"state": "halted", "alreadyHalted": True, **self._last_stop_fields()}
        if state != "running":
            raise RenodeSessionError(f"Cannot halt target from state '{state}'")
        self.client.interrupt()
        if not self._run_stopped.wait(timeout=max(self.client.timeout, 1.0) * 2.0):
            raise TimeoutError("Renode did not acknowledge the GDB interrupt")
        if self._run_error is not None:
            raise RenodeSessionError(f"Renode continue operation failed: {self._run_error}") from self._run_error
        return {"state": "halted", **self._last_stop_fields()}

    def step_target(self, *, ufex: bool = False) -> Dict[str, Any]:
        del ufex
        self._require_halted()
        stop = self.client.step()
        with self._state_lock:
            self._last_stop = stop
            self._debug_state = "halted"
        result = {"state": "halted", **self._stop_dict(stop)}
        result.update(self.get_pc())
        return result

    def reset_target(self) -> Dict[str, Any]:
        if self._debug_state == "running":
            self.halt_target()
        self._require_halted()
        output = self.client.remote_command("machine Reset")
        pc_result = self.set_pc(self.reset_pc)
        with self._state_lock:
            self._last_stop = None
            self._debug_state = "halted"
        return {
            "state": "halted",
            "command": "machine Reset",
            "output": output,
            **pc_result,
        }

    def target_status(self, *, refresh: bool = True, include_pc: bool = False) -> Dict[str, Any]:
        del refresh
        with self._state_lock:
            state = self._debug_state
            run_error = self._run_error
        result: Dict[str, Any] = {"state": state, "running": state == "running"}
        if run_error is not None:
            result["error"] = str(run_error)
        result.update(self._last_stop_fields())
        if include_pc and state == "halted":
            result.update(self.get_pc())
        return result

    def erase_chip(self, mode: Optional[int] = None) -> Dict[str, Any]:
        return self.erase(mode)

    def erase(self, mode: Optional[int] = None) -> Dict[str, Any]:
        del mode
        self._ensure_halted()
        erased = bytes([0xFF]) * self.transfer_chunk_size
        remaining = self.flash_size
        address = self.flash_base
        chunks = 0
        while remaining:
            size = min(remaining, len(erased))
            self.client.write_memory(address, erased[:size])
            address += size
            remaining -= size
            chunks += 1
        return {
            "backend": "renode-gdb",
            "address": self.flash_base,
            "size": self.flash_size,
            "fill": 0xFF,
            "chunks": chunks,
        }

    def read_program(self, address: int, length: int, *, script_name: str = "ReadProgmem") -> Dict[str, Any]:
        del script_name
        self._ensure_halted()
        if length < 0:
            raise ValueError("length must be non-negative")
        data = self._read_chunked(address, length)
        return {
            "address": address,
            "length": len(data),
            "dataHex": data.hex(),
            "script": "renode-gdb-memory-read",
        }

    def write_program(self, address: int, data: bytes, *, script_name: str = "WriteProgmem") -> Dict[str, Any]:
        del script_name
        self._ensure_halted()
        chunks = self._write_chunked(address, data)
        return {
            "address": address,
            "length": len(data),
            "chunks": chunks,
            "script": "renode-gdb-memory-write",
        }

    def read_memory(self, address: int, length: int) -> Dict[str, Any]:
        return self.read_program(address, length)

    def write_memory(self, address: int, data: bytes) -> Dict[str, Any]:
        return self.write_program(address, data)

    def program_hex(
        self,
        path: str,
        *,
        erase_first: bool = True,
        verify: bool = False,
        chunk_size: int = 256,
    ) -> Dict[str, Any]:
        self._ensure_halted()
        image = FirmwareImage.from_path(path)
        erase_result = self.erase() if erase_first else None
        programmed = []
        for segment in image.segments:
            target_address = self._image_target_address(segment.address, len(segment.data))
            chunks = self._write_chunked(target_address, segment.data, chunk_size=chunk_size)
            programmed.append(
                {
                    "address": segment.address,
                    "targetAddress": target_address,
                    "size": len(segment.data),
                    "chunks": chunks,
                }
            )
        result: Dict[str, Any] = {
            "path": path,
            "erase": erase_result,
            "segments": programmed,
            "bytesProgrammed": sum(item["size"] for item in programmed),
        }
        if verify:
            result["verify"] = self.verify_hex(path, chunk_size=chunk_size)
        return result

    def verify_hex(self, path: str, *, chunk_size: int = 256) -> Dict[str, Any]:
        self._ensure_halted()
        image = FirmwareImage.from_path(path)
        verified = []
        for segment in image.segments:
            target_start = self._image_target_address(segment.address, len(segment.data))
            chunks = 0
            offset = 0
            while offset < len(segment.data):
                expected = segment.data[offset : offset + chunk_size]
                address = target_start + offset
                actual = self.client.read_memory(address, len(expected))
                if actual != expected:
                    mismatch = next(
                        index for index, (got, want) in enumerate(zip(actual, expected)) if got != want
                    )
                    absolute = address + mismatch
                    raise RenodeSessionError(
                        f"Verification failed at 0x{absolute:X}: "
                        f"read 0x{actual[mismatch]:02X}, expected 0x{expected[mismatch]:02X}"
                    )
                offset += len(expected)
                chunks += 1
            verified.append(
                {
                    "address": segment.address,
                    "targetAddress": target_start,
                    "size": len(segment.data),
                    "chunks": chunks,
                }
            )
        return {
            "path": path,
            "segments": verified,
            "bytesVerified": sum(item["size"] for item in verified),
            "verified": True,
        }

    def _image_target_address(self, address: int, length: int) -> int:
        """Map an image's logical program address onto Renode's flat sysbus.

        PIC16, PIC18 and dsPIC33 expose program storage at the same address used
        by their firmware images.  The dsPIC30 Renode platform is Harvard and
        places program flash at 0x100000 to keep it separate from data space;
        normal dsPIC30 HEX/ELF files still start user code at logical address 0.
        Images that are already rebased into the Renode window are accepted as
        well, which avoids double relocation in custom test fixtures.
        """
        if address < 0 or length < 0:
            raise ValueError("image address and length must be non-negative")
        flash_end = self.flash_base + self.flash_size
        if self.flash_base <= address and address + length <= flash_end:
            return address
        target = address + self.image_address_bias
        if target < self.flash_base or target + length > flash_end:
            raise RenodeSessionError(
                f"Image range 0x{address:X}..0x{address + max(length - 1, 0):X} "
                f"does not fit Renode flash 0x{self.flash_base:X}..0x{flash_end - 1:X}"
            )
        return target

    def add_breakpoint(self, address: int, *, kind: int = 2, slot: Optional[int] = None) -> Dict[str, Any]:
        self._ensure_halted()
        slot = self._allocate_slot(slot)
        if not self.client.set_hw_breakpoint(address, kind):
            raise RenodeSessionError(f"Renode rejected hardware breakpoint at 0x{address:X}")
        self._hardware_slots[slot] = {"type": "execute", "address": address, "kind": kind}
        return {"slot": slot, "address": address, "kind": kind, "backend": "renode-gdb"}

    def remove_breakpoint(self, address: int, *, slot: Optional[int] = None) -> Dict[str, Any]:
        self._ensure_halted()
        slot, item = self._find_slot("execute", address, slot)
        if not self.client.clear_hw_breakpoint(item["address"], item["kind"]):
            raise RenodeSessionError(f"Renode rejected breakpoint removal at 0x{address:X}")
        del self._hardware_slots[slot]
        return {"slot": slot, "address": item["address"], "removed": True}

    def add_watchpoint(
        self,
        address: int,
        *,
        length: int = 1,
        access: str = "access",
        slot: Optional[int] = None,
    ) -> Dict[str, Any]:
        self._ensure_halted()
        access_key = access.strip().lower()
        setters = {
            "read": self.client.set_read_watchpoint,
            "write": self.client.set_write_watchpoint,
            "access": self.client.set_access_watchpoint,
        }
        if access_key not in setters:
            raise ValueError("access must be 'read', 'write', or 'access'")
        slot = self._allocate_slot(slot)
        if not setters[access_key](address, length):
            raise RenodeSessionError(f"Renode rejected {access_key} watchpoint at 0x{address:X}")
        self._hardware_slots[slot] = {
            "type": "watch",
            "address": address,
            "length": length,
            "access": access_key,
        }
        return {
            "slot": slot,
            "address": address,
            "length": length,
            "access": access_key,
            "backend": "renode-gdb",
        }

    def remove_watchpoint(self, address: int, *, slot: Optional[int] = None) -> Dict[str, Any]:
        self._ensure_halted()
        slot, item = self._find_slot("watch", address, slot)
        clearers = {
            "read": self.client.clear_read_watchpoint,
            "write": self.client.clear_write_watchpoint,
            "access": self.client.clear_access_watchpoint,
        }
        if not clearers[item["access"]](item["address"], item["length"]):
            raise RenodeSessionError(f"Renode rejected watchpoint removal at 0x{address:X}")
        del self._hardware_slots[slot]
        return {"slot": slot, "address": item["address"], "removed": True}

    def run_script(self, name: str, *params: Any, timeout_ms: int = -1) -> Dict[str, Any]:
        del params, timeout_ms
        raise RenodeSessionError(
            f"RI4 device-pack script '{name}' is unavailable with the Renode GDB backend"
        )

    def run_script_with_upload(self, name: str, expected_length: int, *params: Any) -> bytes:
        del expected_length, params
        raise RenodeSessionError(
            f"RI4 device-pack script '{name}' is unavailable with the Renode GDB backend"
        )

    def run_script_with_download(self, name: str, data: bytes, *params: Any, timeout_ms: int = -1) -> Dict[str, Any]:
        del data, params, timeout_ms
        raise RenodeSessionError(
            f"RI4 device-pack script '{name}' is unavailable with the Renode GDB backend"
        )

    def _ensure_halted(self) -> None:
        if self._debug_state == "running":
            self.halt_target()
        self._require_halted()

    def _require_halted(self) -> None:
        if self._debug_state != "halted":
            raise RenodeSessionError(f"Target must be halted; current state is '{self._debug_state}'")

    def _read_chunked(self, address: int, length: int) -> bytes:
        out = bytearray()
        while len(out) < length:
            size = min(self.transfer_chunk_size, length - len(out))
            out.extend(self.client.read_memory(address + len(out), size))
        return bytes(out)

    def _write_chunked(self, address: int, data: bytes, *, chunk_size: Optional[int] = None) -> int:
        effective = self.transfer_chunk_size if chunk_size is None else min(chunk_size, self.transfer_chunk_size)
        if effective <= 0:
            raise ValueError("chunk_size must be positive")
        offset = 0
        chunks = 0
        while offset < len(data):
            chunk = data[offset : offset + effective]
            self.client.write_memory(address + offset, chunk)
            offset += len(chunk)
            chunks += 1
        return chunks

    def _allocate_slot(self, requested: Optional[int]) -> int:
        if requested is not None:
            if requested < 0:
                raise ValueError("slot must be non-negative")
            if requested in self._hardware_slots:
                raise RenodeSessionError(f"Hardware slot {requested} is already in use")
            return requested
        slot = 0
        while slot in self._hardware_slots:
            slot += 1
        return slot

    def _find_slot(self, item_type: str, address: int, requested: Optional[int]) -> Tuple[int, Dict[str, Any]]:
        if requested is not None:
            item = self._hardware_slots.get(requested)
            if item is None or item.get("type") != item_type:
                raise RenodeSessionError(f"No {item_type} resource in slot {requested}")
            return requested, item
        for slot, item in self._hardware_slots.items():
            if item.get("type") == item_type and item.get("address") == address:
                return slot, item
        raise RenodeSessionError(f"No {item_type} resource found at 0x{address:X}")

    def _last_stop_fields(self) -> Dict[str, Any]:
        return {} if self._last_stop is None else self._stop_dict(self._last_stop)

    @staticmethod
    def _stop_dict(stop: StopReply) -> Dict[str, Any]:
        return {"stopReply": stop.raw, "stopKind": stop.kind, "signal": stop.signal}
