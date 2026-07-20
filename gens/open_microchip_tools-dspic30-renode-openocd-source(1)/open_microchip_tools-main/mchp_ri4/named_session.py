from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from mchp_simulator.firmware_image import FirmwareImage, Segment

from .commands import Commands
from .device_file import DeviceFile
from .errors import Ri4ProtocolError
from .family_profiles import FamilyProfile, get_family_profile
from .icd4_comms_usb import ICD4CommsUsb
from .ri4_com import Ri4Com
from .transport import PyusbTransport


def _decode_le_u32(data: bytes) -> int:
    padded = data[:4].ljust(4, b"\x00")
    return int.from_bytes(padded, "little", signed=False)


@dataclass
class NamedScriptSession:
    PROGRAM_SCRIPT_TIMEOUT_MS = 30_000

    """Execute named RI4 scripts loaded from scripts.xml/tool.xml content."""

    commands: Commands
    device_file: DeviceFile
    tool_file: Optional[DeviceFile] = None
    tool: str = "RI4"
    processor: str = ""
    vid: Optional[int] = None
    pid: Optional[int] = None
    pc_bytes: int = 4
    family: Optional[str] = None
    profile: Optional[FamilyProfile] = None
    _debug_state: str = field(default="unknown", init=False, repr=False)
    _last_halt_status: Optional[int] = field(default=None, init=False, repr=False)
    _hardware_slots: Dict[int, Dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _xmega_data_breakpoint_types: Dict[int, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.family is not None:
            self.family = self.family.strip().upper()
        if self.profile is None and self.family is not None:
            self.profile = get_family_profile(self.family)

    @classmethod
    def open_usb(
        cls,
        *,
        tool: str,
        processor: str,
        vid: int,
        pid: int,
        scripts_path: str,
        tool_scripts_path: Optional[str] = None,
        script_suffix: Optional[str] = None,
        pc_bytes: int = 4,
        family: Optional[str] = None,
        serial_number: Optional[str] = None,
        reset_device: bool = False,
    ) -> "NamedScriptSession":
        device_file = DeviceFile.from_xml_path(processor, scripts_path)
        if script_suffix:
            device_file.set_script_suffix(script_suffix)

        tool_file = None
        if tool_scripts_path:
            tool_file = DeviceFile.from_xml_path(processor, tool_scripts_path)
            if script_suffix:
                tool_file.set_script_suffix(script_suffix)

        comm = ICD4CommsUsb(
            Ri4Com(
                PyusbTransport(
                    vid=vid,
                    pid=pid,
                    serial_number=serial_number,
                    reset_device=reset_device,
                )
            )
        )
        return cls(
            commands=Commands(comm),
            device_file=device_file,
            tool_file=tool_file,
            tool=tool.upper(),
            processor=processor,
            vid=vid,
            pid=pid,
            pc_bytes=pc_bytes,
            family=family.strip().upper() if family else None,
            profile=get_family_profile(family),
        )

    def has_script(self, name: str) -> bool:
        return self._lookup_script(name) is not None

    def script_inventory(self) -> Dict[str, Any]:
        device_names = [script.method for script in self.device_file.getScripts()]
        tool_names = [script.method for script in self.tool_file.getScripts()] if self.tool_file is not None else []
        result = {
            "tool": self.tool,
            "processor": self.processor,
            "vid": None if self.vid is None else f"0x{self.vid:04X}",
            "pid": None if self.pid is None else f"0x{self.pid:04X}",
            "pcBytes": self.pc_bytes,
            "deviceScriptCount": len(device_names),
            "toolScriptCount": len(tool_names),
            "sampleScripts": sorted((device_names + tool_names))[:16],
        }
        if self.family is not None:
            result["family"] = self.family
        if self.profile is not None:
            result["profile"] = self.profile.to_dict()
        result["capabilities"] = self.capabilities()
        result["debugState"] = self._debug_state
        return result

    def close(self) -> None:
        try:
            if self._debug_state in {"halted", "running"} and self.has_script("ExitDebugMode"):
                try:
                    self.run_script("ExitDebugMode")
                except Exception:
                    self._preclean_scripting_engine()
        finally:
            self._debug_state = "unknown"
            self.commands.close()

    def run_script(self, name: str, *params: Any, timeout_ms: int = -1) -> Dict[str, Any]:
        script = self._require_script(name)
        result = self.commands.run_script_basic(script.getData(), *params, timeout_ms=timeout_ms)
        payload = result.payload.hex() if result.payload else ""
        return {"script": script.method, "status": result.status, "payloadHex": payload}

    def run_script_with_upload(self, name: str, expected_length: int, *params: Any) -> bytes:
        script = self._require_script(name)
        return self.commands.run_script_with_upload(script.getData(), expected_length, *params)

    def run_script_with_download(self, name: str, data: bytes, *params: Any, timeout_ms: int = -1) -> Dict[str, Any]:
        script = self._require_script(name)
        result = self.commands.run_script_with_download(script.getData(), data, *params, timeout_ms=timeout_ms)
        payload = result.payload.hex() if result.payload else ""
        return {"script": script.method, "status": result.status, "payloadHex": payload}

    def enter_debug_mode(self) -> Dict[str, Any]:
        candidates = self.profile.enter_debug_scripts if self.profile is not None else ("EnterDebugMode",)
        result = self.run_first(candidates)
        self._debug_state = "halted"
        return result

    def get_pc(self) -> Dict[str, Any]:
        candidates = self.profile.get_pc_scripts if self.profile is not None else ("GetPC",)
        data = self.run_first_with_upload(candidates, self.pc_bytes, (0, self.pc_bytes), ())
        return {"pc": _decode_le_u32(data), "rawHex": data.hex()}

    def set_pc(self, address: int) -> Dict[str, Any]:
        candidates = self.profile.set_pc_scripts if self.profile is not None else ("SetPC",)
        if not candidates:
            raise Ri4ProtocolError(f"Set PC is not modeled for family '{self.family or 'generic'}'")
        return self.run_first(candidates, address)

    def run_target(self) -> Dict[str, Any]:
        candidates = self.profile.run_scripts if self.profile is not None else ("Run",)
        result = self.run_first(candidates)
        self._debug_state = "running"
        return result

    def step_target(self, *, ufex: bool = False) -> Dict[str, Any]:
        candidates = self.profile.step_scripts if self.profile is not None else ("SingleStep", "SingleStepUFEX")
        ordered = tuple(name for name in candidates if (not ufex or name == "SingleStepUFEX" or name == "SingleStep"))
        if ufex and self.has_script("SingleStepUFEX"):
            result = self.run_script("SingleStepUFEX")
        else:
            result = self.run_first(ordered or candidates)
        self._debug_state = "halted"
        return result

    def halt_target(self) -> Dict[str, Any]:
        candidates = self.profile.halt_scripts if self.profile is not None else ("Halt",)
        result = self.run_first(candidates)
        self._debug_state = "halted"
        return result

    def exit_debug_mode(self) -> Optional[Dict[str, Any]]:
        if not self.has_script("ExitDebugMode"):
            self._debug_state = "unknown"
            return None
        result = self.run_script("ExitDebugMode")
        self._debug_state = "unknown"
        return result

    def reset_target(self) -> Dict[str, Any]:
        candidates = tuple(
            name for name in ("DebugReset", "SysReset", "ResetandBoot") if self.has_script(name)
        )
        if not candidates:
            raise Ri4ProtocolError(f"Target reset is not supported for family '{self.family or 'generic'}'")
        result = self.run_first(candidates)
        self._debug_state = "halted" if result.get("script") == "DebugReset" else "unknown"
        return result

    def capabilities(self) -> Dict[str, bool]:
        profile = self.profile
        write_scripts = profile.write_program_scripts if profile is not None else ("WriteProgmem",)
        read_scripts = profile.read_program_scripts if profile is not None else ("ReadProgmem",)
        erase_scripts = profile.erase_scripts if profile is not None else ("EraseChip",)
        enter_debug_scripts = profile.enter_debug_scripts if profile is not None else ("EnterDebugMode",)
        run_scripts = profile.run_scripts if profile is not None else ("Run",)
        halt_scripts = profile.halt_scripts if profile is not None else ("Halt",)
        step_scripts = profile.step_scripts if profile is not None else ("SingleStep", "SingleStepUFEX")
        get_pc_scripts = profile.get_pc_scripts if profile is not None else ("GetPC",)
        set_pc_scripts = profile.set_pc_scripts if profile is not None else ("SetPC",)
        halt_status_scripts = profile.halt_status_scripts if profile is not None else ("GetHaltStatus",)
        set_hw_scripts = profile.set_hw_breakpoint_scripts if profile is not None else ("SetHWBP",)
        set_data_scripts = profile.set_data_breakpoint_scripts if profile is not None else ("SetDataHWBP",)
        clear_hw_scripts = profile.clear_hw_breakpoint_scripts if profile is not None else ("ClearHWBP",)
        return {
            "flash": self._has_any_script(write_scripts),
            "erase": self._has_any_script(erase_scripts),
            "verify": self._has_any_script(read_scripts),
            "debug": all(
                (
                    self._has_any_script(enter_debug_scripts),
                    self._has_any_script(run_scripts),
                    self._has_any_script(halt_scripts),
                    self._has_any_script(step_scripts),
                    self._has_any_script(get_pc_scripts),
                )
            ),
            "poll": self._has_any_script(halt_status_scripts),
            "setPc": self._has_any_script(set_pc_scripts),
            "breakpoints": self._has_any_script(set_hw_scripts) and self._has_any_script(clear_hw_scripts),
            "watchpoints": self._has_any_script(set_data_scripts) and self._has_any_script(clear_hw_scripts),
            "reset": self._has_any_script(("DebugReset", "SysReset", "ResetandBoot")),
            # RI4 ReadProgmem/WriteProgmem are programming-mode operations.  They are
            # intentionally not advertised as arbitrary debugger memory access: doing so
            # makes GDB believe RAM, stack and peripheral reads are safe when the script
            # pack only exposes program-memory services.
            "programRead": self._has_any_script(read_scripts),
            "programWrite": self._has_any_script(write_scripts),
            "memoryRead": False,
            "memoryWrite": False,
        }

    def is_running(self) -> Dict[str, Any]:
        candidates = self.profile.halt_status_scripts if self.profile is not None else ("GetHaltStatus",)
        if not candidates:
            raise Ri4ProtocolError(f"Target polling is not supported for family '{self.family or 'generic'}'")
        result = self.run_first(candidates)
        payload = bytes.fromhex(str(result.get("payloadHex", "")))
        if len(payload) != 4:
            raise Ri4ProtocolError(f"GetHaltStatus returned {len(payload)} bytes; expected 4")
        halt_status = int.from_bytes(payload, "little", signed=True)
        halted = halt_status == -1431655766  # 0xAAAAAAAA, matching the MPLAB RI4 controller contract.
        if halted and self._last_halt_status != halt_status:
            post_halt = self.profile.post_halt_scripts if self.profile is not None else ("PostHalt",)
            available = tuple(name for name in post_halt if self.has_script(name))
            if available:
                self.run_first(available)
        self._last_halt_status = halt_status
        self._debug_state = "halted" if halted else "running"
        return {
            "running": not halted,
            "state": self._debug_state,
            "haltStatus": halt_status,
            "haltStatusHex": payload.hex(),
        }

    def target_status(self, *, refresh: bool = True, include_pc: bool = False) -> Dict[str, Any]:
        status: Dict[str, Any]
        if refresh and self.capabilities()["poll"]:
            status = self.is_running()
        else:
            status = {"running": self._debug_state == "running", "state": self._debug_state}
        if include_pc and status["state"] == "halted":
            status.update(self.get_pc())
        return status

    def add_breakpoint(self, address: int, *, kind: int = 2, slot: Optional[int] = None) -> Dict[str, Any]:
        if not self.capabilities()["breakpoints"]:
            raise Ri4ProtocolError(f"Hardware breakpoints are not supported for family '{self.family or 'generic'}'")
        slot = self._allocate_hardware_slot(slot)
        candidates = self.profile.set_hw_breakpoint_scripts if self.profile is not None else ("SetHWBP",)
        result = self.run_first(candidates, slot, address)
        self._hardware_slots[slot] = {"type": "execute", "address": address, "kind": kind}
        return {"slot": slot, "address": address, "kind": kind, "script": result.get("script", "")}

    def remove_breakpoint(self, address: int, *, slot: Optional[int] = None) -> Dict[str, Any]:
        slot = self._find_hardware_slot("execute", address, slot)
        return self._clear_hardware_slot(slot)

    def add_watchpoint(
        self,
        address: int,
        *,
        length: int = 1,
        access: str = "access",
        slot: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self.capabilities()["watchpoints"]:
            raise Ri4ProtocolError(f"Watchpoints are not supported for family '{self.family or 'generic'}'")
        access_key = access.strip().lower()
        type_ordinal = {"read": 1, "write": 2, "access": 3}.get(access_key)
        if type_ordinal is None:
            raise ValueError("access must be 'read', 'write', or 'access'")
        slot = self._allocate_hardware_slot(slot)
        candidates = self.profile.set_data_breakpoint_scripts if self.profile is not None else ("SetDataHWBP",)
        script_type = type_ordinal
        if "XMEGA" in self.processor.upper() and slot < 2:
            self._xmega_data_breakpoint_types[slot] = type_ordinal
            script_type = (self._xmega_data_breakpoint_types.get(0, 0) << 2) | self._xmega_data_breakpoint_types.get(1, 0)
        result = self.run_first(candidates, script_type, slot, address)
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
            "script": result.get("script", ""),
        }

    def remove_watchpoint(self, address: int, *, slot: Optional[int] = None) -> Dict[str, Any]:
        slot = self._find_hardware_slot("watch", address, slot)
        self._xmega_data_breakpoint_types.pop(slot, None)
        return self._clear_hardware_slot(slot)

    def erase_chip(self, mode: Optional[int] = None) -> Dict[str, Any]:
        candidates = self.profile.erase_scripts if self.profile is not None else ("EraseChip",)
        if mode is None:
            return self.run_first(candidates, timeout_ms=self.PROGRAM_SCRIPT_TIMEOUT_MS)
        return self.run_first(candidates, mode, timeout_ms=self.PROGRAM_SCRIPT_TIMEOUT_MS)

    def read_program(self, address: int, length: int, *, script_name: str = "ReadProgmem") -> Dict[str, Any]:
        candidates = (script_name,) if script_name else ()
        if self.profile is not None and script_name == "ReadProgmem":
            candidates = self.profile.read_program_scripts
        elif not candidates:
            candidates = ("ReadProgmem",)
        data, used = self.run_first_with_upload_named(candidates, length, (address, length))
        return {"address": address, "length": len(data), "dataHex": data.hex(), "script": used}

    def write_program(self, address: int, data: bytes, *, script_name: str = "WriteProgmem") -> Dict[str, Any]:
        candidates = (script_name,) if script_name else ()
        if self.profile is not None and script_name == "WriteProgmem":
            candidates = self.profile.write_program_scripts
        elif not candidates:
            candidates = ("WriteProgmem",)
        return self.run_first_with_download(
            candidates,
            data,
            address,
            len(data),
            timeout_ms=self.PROGRAM_SCRIPT_TIMEOUT_MS,
        )

    def enter_programming_mode(self) -> Optional[Dict[str, Any]]:
        if self.profile is None or not self.profile.program_entry_scripts:
            return None
        self._preclean_scripting_engine()
        self._apply_icsp_speed_if_available()
        available = tuple(name for name in self.profile.program_entry_scripts if self.has_script(name))
        if not available:
            return None
        return self.run_first(available)

    def exit_programming_mode(self) -> Optional[Dict[str, Any]]:
        if self.profile is None or not self.profile.program_exit_scripts:
            return None
        available = tuple(name for name in self.profile.program_exit_scripts if self.has_script(name))
        if not available:
            return None
        return self.run_first(available)

    def erase(self, mode: Optional[int] = None) -> Dict[str, Any]:
        program_entered = self.enter_programming_mode()
        program_exited: Optional[Dict[str, Any]] = None
        primary_error: Optional[BaseException] = None
        try:
            erase_result = self.erase_chip(mode)
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                if program_entered is not None:
                    program_exited = self.exit_programming_mode()
            except Exception:
                self._preclean_scripting_engine()
                if primary_error is None:
                    raise
        return {"erase": erase_result, "programEntry": program_entered, "programExit": program_exited}

    def verify_hex(self, path: str, *, chunk_size: int = 256) -> Dict[str, Any]:
        image = FirmwareImage.from_path(path)
        program_entered = self.enter_programming_mode()
        program_exited: Optional[Dict[str, Any]] = None
        primary_error: Optional[BaseException] = None
        verified_segments = []
        try:
            for segment in image.segments:
                chunks = 0
                for address, expected in self._iter_program_chunks(segment.address, segment.data, chunk_size):
                    self._verify_program_chunk(address, expected)
                    chunks += 1
                verified_segments.append({"address": segment.address, "size": len(segment.data), "chunks": chunks})
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                if program_entered is not None:
                    program_exited = self.exit_programming_mode()
            except Exception:
                self._preclean_scripting_engine()
                if primary_error is None:
                    raise
        return {
            "imagePath": path,
            "segmentCount": len(verified_segments),
            "segments": verified_segments,
            "verified": True,
            "programEntry": program_entered,
            "programExit": program_exited,
        }

    def program_hex(
        self,
        path: str,
        *,
        erase_first: bool = True,
        verify: bool = False,
        chunk_size: int = 256,
    ) -> Dict[str, Any]:
        image = FirmwareImage.from_path(path)
        program_entered = self.enter_programming_mode()
        program_exited: Optional[Dict[str, Any]] = None
        primary_error: Optional[BaseException] = None
        segments = []
        try:
            if erase_first:
                self.erase_chip()

            for segment in image.segments:
                write_script = ""
                chunks = 0
                for address, data in self._iter_program_chunks(segment.address, segment.data, chunk_size):
                    write_result = self.write_program(address, data)
                    write_script = str(write_result.get("script", write_script))
                    if verify:
                        self._verify_program_chunk(address, data)
                    chunks += 1
                segments.append(
                    {
                        "address": segment.address,
                        "size": len(segment.data),
                        "chunks": chunks,
                        "writeScript": write_script,
                    }
                )
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                if program_entered is not None:
                    program_exited = self.exit_programming_mode()
            except Exception:
                self._preclean_scripting_engine()
                if primary_error is None:
                    raise

        return {
            "imagePath": path,
            "segmentCount": len(segments),
            "segments": segments,
            "erased": erase_first,
            "verified": verify,
            "chunkSize": chunk_size,
            "programEntry": program_entered,
            "programExit": program_exited,
        }

    def read_memory(self, address: int, length: int) -> Dict[str, Any]:
        return self.read_program(address, length)

    def write_memory(self, address: int, data: bytes) -> Dict[str, Any]:
        return self.write_program(address, data)

    def read_program_range(self, start_address: int, length: int, *, chunk_size: int = 64) -> FirmwareImage:
        if length < 0:
            raise ValueError("length must be non-negative")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        effective_chunk_size = self._effective_read_chunk_size(chunk_size)

        segments = []
        address = start_address
        offset = 0
        while offset < length:
            requested_len = min(effective_chunk_size, length - offset)
            transfer_len = self._effective_read_transfer_length(requested_len, effective_chunk_size)
            result = self.read_program(address, transfer_len)
            data = bytes.fromhex(str(result["dataHex"]))
            segments.append(Segment(address=start_address + offset, data=data[:requested_len]))
            offset += requested_len
            address += self._buffer_size_to_program_address(transfer_len)
        return FirmwareImage(segments=tuple(segments))

    def dump_program_hex(
        self,
        path: str,
        *,
        start_address: int,
        length: int,
        chunk_size: int = 64,
        enter_programming: bool = True,
    ) -> Dict[str, Any]:
        effective_chunk_size = self._effective_read_chunk_size(chunk_size)
        program_entered = self.enter_programming_mode() if enter_programming else None
        program_exited: Optional[Dict[str, Any]] = None
        primary_error: Optional[BaseException] = None
        try:
            image = self.read_program_range(start_address, length, chunk_size=chunk_size)
            image.to_intel_hex_path(path)
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                if enter_programming and program_entered is not None:
                    program_exited = self.exit_programming_mode()
            except Exception:
                self._preclean_scripting_engine()
                if primary_error is None:
                    raise
        return {
            "imagePath": path,
            "startAddress": start_address,
            "length": length,
            "chunkSize": chunk_size,
            "effectiveChunkSize": effective_chunk_size,
            "segmentCount": len(image.segments),
            "programEntry": program_entered,
            "programExit": program_exited,
        }

    def _first_available_script(self, script_names: Sequence[str], operation: str) -> str:
        for name in script_names:
            if self.has_script(name):
                return name
        raise Ri4ProtocolError(
            f"None of the candidate {operation} scripts are available for processor "
            f"'{self.processor}': {', '.join(script_names)}"
        )

    def run_first(self, script_names: Sequence[str], *params: Any, timeout_ms: int = -1) -> Dict[str, Any]:
        # Candidate names are aliases selected from the script inventory, not a
        # retry policy.  Replaying a failed erase/run/write against a second
        # script can duplicate a non-idempotent operation after a transport
        # timeout, so execute exactly one available implementation.
        name = self._first_available_script(script_names, "basic")
        return self.run_script(name, *params, timeout_ms=timeout_ms)

    def run_first_with_upload(
        self,
        script_names: Sequence[str],
        expected_length: int,
        primary_params: Sequence[Any],
        secondary_params: Sequence[Any] = (),
    ) -> bytes:
        data, _ = self.run_first_with_upload_named(
            script_names, expected_length, tuple(primary_params), tuple(secondary_params)
        )
        return data

    def run_first_with_upload_named(
        self,
        script_names: Sequence[str],
        expected_length: int,
        primary_params: Sequence[Any],
        secondary_params: Sequence[Any] = (),
    ) -> Tuple[bytes, str]:
        # secondary_params is retained for API compatibility only.  Automatic
        # replays are unsafe because a response timeout does not prove the
        # target-side operation did not execute.
        del secondary_params
        name = self._first_available_script(script_names, "upload")
        return self.run_script_with_upload(name, expected_length, *tuple(primary_params)), name

    def run_first_with_download(
        self,
        script_names: Sequence[str],
        data: bytes,
        *params: Any,
        timeout_ms: int = -1,
    ) -> Dict[str, Any]:
        name = self._first_available_script(script_names, "download")
        return self.run_script_with_download(name, data, *params, timeout_ms=timeout_ms)

    def _verify_program_chunk(self, address: int, expected: bytes) -> None:
        read_result = self.read_program(address, len(expected))
        actual = bytes.fromhex(str(read_result["dataHex"]))
        if actual != expected:
            mismatch = next((i for i, (left, right) in enumerate(zip(expected, actual)) if left != right), 0)
            width = self._program_data_width()
            mismatch_address = address + (mismatch // width) * self._program_address_increment()
            raise Ri4ProtocolError(
                f"Verify failed at 0x{mismatch_address:x}: expected {expected[mismatch:mismatch + 16].hex()} "
                f"got {actual[mismatch:mismatch + 16].hex()}"
            )

    def _iter_program_chunks(self, address: int, data: bytes, chunk_size: int) -> Iterable[Tuple[int, bytes]]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        width = self._program_data_width()
        if width > 1 and len(data) % width != 0:
            raise Ri4ProtocolError(
                f"Program data length {len(data)} is not aligned to family "
                f"'{self.family or 'generic'}' width {width}"
            )
        effective = chunk_size if width <= 1 else chunk_size - (chunk_size % width)
        if effective <= 0:
            raise Ri4ProtocolError(
                f"Program chunk size {chunk_size} is too small for family '{self.family or 'generic'}' width {width}"
            )
        offset = 0
        target_address = address
        while offset < len(data):
            remaining = len(data) - offset
            size = min(effective, remaining)
            if size < remaining and width > 1:
                size -= size % width
            chunk = data[offset : offset + size]
            if not chunk:
                raise Ri4ProtocolError("Unable to make progress while chunking program data")
            yield target_address, chunk
            offset += len(chunk)
            if offset < len(data):
                target_address += self._buffer_size_to_program_address(len(chunk))

    def _has_any_script(self, names: Sequence[str]) -> bool:
        return any(self.has_script(name) for name in names)

    def _allocate_hardware_slot(self, requested: Optional[int]) -> int:
        if requested is not None:
            if requested < 0 or requested > 255:
                raise ValueError("slot must be between 0 and 255")
            if requested in self._hardware_slots:
                raise Ri4ProtocolError(f"Hardware breakpoint slot {requested} is already in use")
            return requested
        for slot in range(4):
            if slot not in self._hardware_slots:
                return slot
        raise Ri4ProtocolError("No free hardware breakpoint/watchpoint slots")

    def _find_hardware_slot(self, item_type: str, address: int, requested: Optional[int]) -> int:
        if requested is not None:
            item = self._hardware_slots.get(requested)
            if item is None or item.get("type") != item_type:
                raise Ri4ProtocolError(f"Hardware slot {requested} does not contain a matching {item_type}")
            return requested
        for slot, item in self._hardware_slots.items():
            if item.get("type") == item_type and item.get("address") == address:
                return slot
        raise Ri4ProtocolError(f"No {item_type} is registered at 0x{address:x}")

    def _clear_hardware_slot(self, slot: int) -> Dict[str, Any]:
        candidates = self.profile.clear_hw_breakpoint_scripts if self.profile is not None else ("ClearHWBP",)
        result = self.run_first(candidates, slot)
        previous = self._hardware_slots.pop(slot)
        return {"slot": slot, "cleared": True, "previous": previous, "script": result.get("script", "")}

    def _lookup_script(self, name: str):
        script = self.device_file.getScriptBasic(name)
        if script is not None:
            return script
        if self.tool_file is not None:
            return self.tool_file.getScriptBasic(name)
        return None

    def _apply_icsp_speed_if_available(self) -> None:
        if self.has_script("SetSpeedFromDevice"):
            last_error: Optional[Exception] = None
            for _ in range(2):
                try:
                    self.run_script("SetSpeedFromDevice")
                    return
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise last_error

    def _preclean_scripting_engine(self) -> None:
        abort = getattr(self.commands.comm, "abort_scripting_engine", None)
        if abort is None:
            return
        try:
            abort()
        except Exception:
            return

    def _effective_read_chunk_size(self, requested_chunk_size: int) -> int:
        effective_chunk_size = requested_chunk_size
        if self.profile is not None and self.profile.max_read_chunk_size > 0:
            effective_chunk_size = min(effective_chunk_size, self.profile.max_read_chunk_size)
        return effective_chunk_size

    def _effective_read_transfer_length(self, requested_length: int, max_chunk_size: int) -> int:
        fixed_window_size = self._fixed_read_window_size()
        if fixed_window_size > 0:
            return fixed_window_size
        width = self._program_data_width()
        if width <= 1:
            return requested_length
        aligned = ((requested_length + width - 1) // width) * width
        if aligned <= max_chunk_size:
            return aligned
        fallback = max_chunk_size - (max_chunk_size % width)
        if fallback <= 0:
            raise Ri4ProtocolError(
                f"Read chunk size {max_chunk_size} is too small for family '{self.family or 'generic'}' width {width}"
            )
        return fallback

    def _buffer_size_to_program_address(self, buffer_size: int) -> int:
        width = self._program_data_width()
        increment = self._program_address_increment()
        if width <= 1:
            return buffer_size
        if buffer_size % width != 0:
            raise Ri4ProtocolError(
                f"Read transfer length {buffer_size} is not aligned to family '{self.family or 'generic'}' width {width}"
            )
        return (buffer_size // width) * increment

    def _program_data_width(self) -> int:
        if self.profile is None:
            return 1
        return max(1, self.profile.program_data_width)

    def _program_address_increment(self) -> int:
        if self.profile is None:
            return 1
        return max(1, self.profile.program_address_increment)

    def _fixed_read_window_size(self) -> int:
        if self.profile is None:
            return 0
        return max(0, self.profile.fixed_read_window_size)

    def _require_script(self, name: str):
        script = self._lookup_script(name)
        if script is None:
            raise Ri4ProtocolError(f"Script '{name}' not found for processor '{self.processor}'")
        return script