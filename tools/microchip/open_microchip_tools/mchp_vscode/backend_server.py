from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, Optional, TextIO

from interfaces.ICD4.icd4_drv import ICD4Driver, ICD4UsbIds
from interfaces.PK4.pk4_drv import PK4Driver, PK4UsbIds
from mchp_ri4.family_profiles import family_inventory
from mchp_ri4.firmware_update import iter_repo_firmware_packages, probe_tool_firmware
from mchp_ri4.named_session import NamedScriptSession
from mchp_simulator import debug_backend
from zephyr_pickit4_replacement.demo import run_stub_demo


class BackendServerError(RuntimeError):
    pass


def _parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise BackendServerError(f"Expected integer-compatible value, got {type(value).__name__}")


def _tool_driver(tool: str, vid: int, pid: int):
    t = (tool or "").strip().lower()
    if t == "pk4":
        return PK4Driver(PK4UsbIds(vid=vid, pid=pid))
    if t == "icd4":
        return ICD4Driver(ICD4UsbIds(vid=vid, pid=pid))
    raise BackendServerError(f"Unsupported tool type: {tool}")


def _parse_string_filter(
    args: Dict[str, Any],
    *,
    singular_key: str,
    plural_key: str,
    match_key: str,
) -> tuple[list[str], str]:
    raw_items = args.get(plural_key)
    raw_item = args.get(singular_key)
    items: list[str] = []
    if isinstance(raw_item, str) and raw_item.strip():
        items.append(raw_item.strip())
    if raw_items is None:
        pass
    elif isinstance(raw_items, list) and all(isinstance(item, str) for item in raw_items):
        items.extend(item.strip() for item in raw_items if item.strip())
    else:
        raise BackendServerError(f"{plural_key} must be a list of strings")
    match = str(args.get(match_key) or "any").strip().lower()
    if match not in {"any", "all"}:
        raise BackendServerError(f"{match_key} must be 'any' or 'all'")
    return items, match


def _parse_optional_string(args: Dict[str, Any], key: str) -> str:
    value = args.get(key, "")
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    raise BackendServerError(f"{key} must be a string")


class BackendServer:
    def __init__(self, *, stdin: TextIO, stdout: TextIO):
        self._stdin = stdin
        self._stdout = stdout
        self._hardware_session: Optional[NamedScriptSession] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            "ping": self._ping,
            "listDevices": self._list_devices,
            "initSession": self._init_session,
            "loadFirmware": self._load_firmware,
            "getStatus": self._get_status,
            "reset": self._reset,
            "halt": self._halt,
            "step": self._step,
            "run": self._run,
            "addBreakpoint": self._add_breakpoint,
            "clearBreakpoints": self._clear_breakpoints,
            "listBreakpoints": self._list_breakpoints,
            "readProgram": self._read_program,
            "probeTool": self._probe_tool,
            "toolFirmwareInventory": self._tool_firmware_inventory,
            "toolProbeFirmware": self._tool_probe_firmware,
            "toolPowerTarget": self._tool_power_target,
            "listHardwareFamilies": self._list_hardware_families,
            "hardwareStartSession": self._hardware_start_session,
            "hardwareSessionStatus": self._hardware_session_status,
            "hardwareEndSession": self._hardware_end_session,
            "hardwareEnterDebugMode": self._hardware_enter_debug_mode,
            "hardwareGetPc": self._hardware_get_pc,
            "hardwareSetPc": self._hardware_set_pc,
            "hardwareRun": self._hardware_run,
            "hardwareStep": self._hardware_step,
            "hardwareHalt": self._hardware_halt,
            "hardwareEraseChip": self._hardware_erase_chip,
            "hardwareProgramHex": self._hardware_program_hex,
            "runZephyrStubDemo": self._run_zephyr_stub_demo,
        }

    def _family_metadata(self, family: Optional[str]) -> Optional[Dict[str, Any]]:
        if not family:
            return None
        for item in family_inventory():
            if str(item.get("family") or "").upper() == family.strip().upper():
                return item
        return None

    def _coerce_family_name(self, family: Any) -> Optional[str]:
        if isinstance(family, str):
            normalized = family.strip()
            return normalized or None
        return None

    def _close_hardware_session(self) -> Optional[Dict[str, Any]]:
        session = self._hardware_session
        if session is None:
            return None
        summary = session.script_inventory()
        try:
            session.close()
        finally:
            self._hardware_session = None
        family_metadata = self._family_metadata(self._coerce_family_name(session.family))
        if family_metadata is not None:
            summary["familyMetadata"] = family_metadata
        return summary

    def serve_forever(self) -> int:
        for raw_line in self._stdin:
            line = raw_line.strip()
            if not line:
                continue
            request_id: Any = None
            try:
                request = json.loads(line)
                request_id = request.get("id")
                response = self._dispatch(request)
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            if request_id is not None:
                response["id"] = request_id
            self._stdout.write(json.dumps(response) + "\n")
            self._stdout.flush()
        return 0

    def _dispatch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        command = str(request.get("command") or "").strip()
        handler = self._handlers.get(command)
        if handler is None:
            raise BackendServerError(f"Unknown command: {command}")
        args = request.get("args") or {}
        result = handler(args)
        return {"ok": True, "result": result}

    def _ping(self, args: Dict[str, Any]) -> Dict[str, str]:
        return {"message": "pong"}

    def _list_devices(self, args: Dict[str, Any]) -> Any:
        return debug_backend.list_devices(str(args.get("prefix") or ""))

    def _init_session(self, args: Dict[str, Any]) -> Any:
        return debug_backend.init_session(str(args.get("device") or ""))

    def _load_firmware(self, args: Dict[str, Any]) -> Any:
        return debug_backend.load_firmware(str(args.get("path") or ""))

    def _get_status(self, args: Dict[str, Any]) -> Any:
        trace_limit = _parse_int(args.get("traceLimit", 200))
        return debug_backend.get_status(trace_limit=trace_limit)

    def _reset(self, args: Dict[str, Any]) -> Any:
        return debug_backend.reset()

    def _halt(self, args: Dict[str, Any]) -> Any:
        return debug_backend.halt()

    def _step(self, args: Dict[str, Any]) -> Any:
        return debug_backend.step()

    def _run(self, args: Dict[str, Any]) -> Any:
        max_steps = _parse_int(args.get("maxSteps", 10000))
        return debug_backend.run(max_steps=max_steps)

    def _add_breakpoint(self, args: Dict[str, Any]) -> Any:
        return debug_backend.add_breakpoint(_parse_int(args.get("address", 0)))

    def _clear_breakpoints(self, args: Dict[str, Any]) -> Any:
        return debug_backend.clear_breakpoints()

    def _list_breakpoints(self, args: Dict[str, Any]) -> Any:
        return debug_backend.list_breakpoints()

    def _read_program(self, args: Dict[str, Any]) -> Any:
        address = _parse_int(args.get("address", 0))
        size = _parse_int(args.get("size", 16))
        return {"data": debug_backend.read_program(address, size)}

    def _probe_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = str(args.get("tool") or "")
        vid = _parse_int(args.get("vid"))
        pid = _parse_int(args.get("pid"))
        keys = args.get("keys") or ["Commands in progress"]
        if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
            raise BackendServerError("keys must be a list of strings")

        driver = _tool_driver(tool, vid, pid)
        values = {key: driver.get_status_value(key) for key in keys}
        return {
            "tool": tool.upper(),
            "vid": f"0x{vid:04X}",
            "pid": f"0x{pid:04X}",
            "status": values,
        }

    def _tool_power_target(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = str(args.get("tool") or "")
        vid = _parse_int(args.get("vid"))
        pid = _parse_int(args.get("pid"))
        voltage_mv = _parse_int(args.get("voltageMv", 5000))
        maintain_active = bool(args.get("maintainActive", True))
        live_connect = bool(args.get("liveConnect", True))
        use_low_voltage_programming = bool(args.get("useLowVoltageProgramming", True))

        driver = _tool_driver(tool, vid, pid)
        try:
            status = driver.power_target(
                voltage_mv,
                from_tool=True,
                maintain_active=maintain_active,
                live_connect=live_connect,
                use_low_voltage_programming=use_low_voltage_programming,
            )
            return {
                "tool": tool.upper(),
                "vid": f"0x{vid:04X}",
                "pid": f"0x{pid:04X}",
                **status,
            }
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()

    def _tool_firmware_inventory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = _parse_optional_string(args, "tool")
        packages = iter_repo_firmware_packages()
        if tool:
            packages = [package for package in packages if package["tool"] == tool.upper()]
        return {"packages": packages}

    def _tool_probe_firmware(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = str(args.get("tool") or "")
        vid = _parse_int(args.get("vid"))
        pid = _parse_int(args.get("pid"))
        return probe_tool_firmware(tool, vid, pid).to_dict()

    def _list_hardware_families(self, args: Dict[str, Any]) -> Any:
        capabilities, capability_match = _parse_string_filter(
            args,
            singular_key="capability",
            plural_key="capabilities",
            match_key="capabilityMatch",
        )
        signatures, signature_match = _parse_string_filter(
            args,
            singular_key="signature",
            plural_key="signatures",
            match_key="signatureMatch",
        )
        groups, group_match = _parse_string_filter(
            args,
            singular_key="group",
            plural_key="groups",
            match_key="groupMatch",
        )
        search_prefix = _parse_optional_string(args, "searchPrefix")
        return family_inventory(
            required_capabilities=capabilities,
            capability_match=capability_match,
            required_signatures=signatures,
            signature_match=signature_match,
            required_groups=groups,
            group_match=group_match,
            search_prefix=search_prefix,
        )

    def _require_hardware_session(self) -> NamedScriptSession:
        if self._hardware_session is None:
            raise BackendServerError("No hardware session is active")
        return self._hardware_session

    def _hardware_start_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = str(args.get("tool") or "")
        processor = str(args.get("processor") or "").strip()
        family = str(args.get("family") or "").strip() or None
        scripts_path = str(args.get("scriptsPath") or "").strip()
        tool_scripts_path = str(args.get("toolScriptsPath") or "").strip() or None
        script_suffix = str(args.get("scriptSuffix") or "").strip() or None
        vid = _parse_int(args.get("vid"))
        pid = _parse_int(args.get("pid"))
        pc_bytes = _parse_int(args.get("pcBytes", 4))
        if not processor:
            raise BackendServerError("processor is required")
        if not scripts_path:
            raise BackendServerError("scriptsPath is required")

        self._close_hardware_session()
        self._hardware_session = NamedScriptSession.open_usb(
            tool=tool,
            processor=processor,
            vid=vid,
            pid=pid,
            scripts_path=scripts_path,
            tool_scripts_path=tool_scripts_path,
            script_suffix=script_suffix,
            pc_bytes=pc_bytes,
            family=family,
        )
        inventory = self._hardware_session.script_inventory()
        session_family = self._coerce_family_name(self._hardware_session.family) or family
        family_metadata = self._family_metadata(session_family)
        inventory["hasDebugScripts"] = all(
            self._hardware_session.has_script(name)
            for name in ("EnterDebugMode", "GetPC", "SetPC", "Run", "SingleStep", "Halt")
        )
        inventory["hasProgrammingScripts"] = all(
            self._hardware_session.has_script(name) for name in ("EraseChip", "WriteProgmem", "ReadProgmem")
        )
        if family_metadata is not None:
            inventory["familyMetadata"] = family_metadata
        return inventory

    def _hardware_session_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        session = self._require_hardware_session()
        inventory = session.script_inventory()
        family_metadata = self._family_metadata(self._coerce_family_name(session.family))
        if family_metadata is not None:
            inventory["familyMetadata"] = family_metadata
        return inventory

    def _hardware_end_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        summary = self._close_hardware_session()
        return {"closed": summary is not None, "previousSession": summary}

    def _hardware_enter_debug_mode(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._require_hardware_session().enter_debug_mode()

    def _hardware_get_pc(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._require_hardware_session().get_pc()

    def _hardware_set_pc(self, args: Dict[str, Any]) -> Dict[str, Any]:
        address = _parse_int(args.get("address", 0))
        return self._require_hardware_session().set_pc(address)

    def _hardware_run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._require_hardware_session().run_target()

    def _hardware_step(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ufex = bool(args.get("ufex", False))
        return self._require_hardware_session().step_target(ufex=ufex)

    def _hardware_halt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._require_hardware_session().halt_target()

    def _hardware_erase_chip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        mode = args.get("mode")
        if mode is None:
            return self._require_hardware_session().erase_chip()
        return self._require_hardware_session().erase_chip(_parse_int(mode))

    def _hardware_program_hex(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = str(args.get("path") or "").strip()
        if not path:
            raise BackendServerError("path is required")
        erase_first = bool(args.get("eraseFirst", True))
        verify = bool(args.get("verify", False))
        return self._require_hardware_session().program_hex(path, erase_first=erase_first, verify=verify)

    def _run_zephyr_stub_demo(self, args: Dict[str, Any]) -> Dict[str, Any]:
        family = str(args.get("family") or "PIC18").strip().upper()
        processor = str(args.get("processor") or "").strip() or ("PIC18F_STUB" if family == "PIC18" else "ATSAME70_STUB")
        write_address = _parse_int(args.get("writeAddress", 0x10))
        write_hex = str(args.get("writeHex") or "01020304").strip()
        try:
            write_data = bytes.fromhex(write_hex)
        except ValueError as exc:
            raise BackendServerError("writeHex must be valid hex") from exc
        result = run_stub_demo(family=family, processor=processor, write_address=write_address, write_data=write_data)
        if not isinstance(result, dict):
            raise BackendServerError("Unexpected Zephyr stub demo result")
        return result


def main() -> int:
    server = BackendServer(stdin=sys.stdin, stdout=sys.stdout)
    return server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())