from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from .commands import Commands
from .device_file import DeviceFile
from .icd4_comms_usb import ICD4CommsUsb
from .named_session import NamedScriptSession
from .power_cli import _discover_pid, _open_driver
from .repo_assets import resolve_repo_scripts_path
from .ri4_com import Ri4Com
from .ri4_debug_cli import TracingTransport
from .transport import PyusbTransport


def _trace_payload(trace_transport: Optional[TracingTransport]) -> list[dict[str, object]]:
    if trace_transport is None:
        return []
    return [entry.to_dict() for entry in trace_transport.trace]


def _write_trace_output(path: str, payload: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _open_session(
    *,
    tool: str,
    processor: str,
    vid: int,
    pid: int,
    scripts_path: str,
    tool_scripts_path: Optional[str],
    script_suffix: Optional[str],
    pc_bytes: int,
    family: Optional[str],
    enable_trace: bool,
) -> tuple[NamedScriptSession, Optional[TracingTransport]]:
    if not enable_trace:
        return (
            NamedScriptSession.open_usb(
                tool=tool,
                processor=processor,
                vid=vid,
                pid=pid,
                scripts_path=scripts_path,
                tool_scripts_path=tool_scripts_path,
                script_suffix=script_suffix,
                pc_bytes=pc_bytes,
                family=family,
            ),
            None,
        )

    tracing_transport = TracingTransport(PyusbTransport(vid=vid, pid=pid))
    device_file = DeviceFile.from_xml_path(processor, scripts_path)
    if script_suffix:
        device_file.set_script_suffix(script_suffix)

    tool_file = None
    if tool_scripts_path:
        tool_file = DeviceFile.from_xml_path(processor, tool_scripts_path)
        if script_suffix:
            tool_file.set_script_suffix(script_suffix)

    session = NamedScriptSession(
        commands=Commands(ICD4CommsUsb(Ri4Com(tracing_transport))),
        device_file=device_file,
        tool_file=tool_file,
        tool=tool.upper(),
        processor=processor,
        vid=vid,
        pid=pid,
        pc_bytes=pc_bytes,
        family=family.strip().upper() if family else None,
    )
    return session, tracing_transport


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read MCU memory to Intel HEX and optionally write it back over a repo-local RI4 hardware session")
    parser.add_argument("--tool", choices=("pk4", "icd4"), default="pk4")
    parser.add_argument("--vid", default="0x04D8")
    parser.add_argument("--pid", default="")
    parser.add_argument("--family", required=True)
    parser.add_argument("--processor", required=True)
    parser.add_argument("--scripts", default="", help="Path to device scripts.xml; defaults to vendored repo assets when available")
    parser.add_argument("--tool-scripts", default="", help="Optional path to tool.xml or equivalent tool scripts bundle")
    parser.add_argument("--script-suffix", default="")
    parser.add_argument("--pc-bytes", type=int, default=4)
    parser.add_argument("--start-address", required=True)
    parser.add_argument("--length", required=True)
    parser.add_argument("--chunk-size", type=int, default=64)
    parser.add_argument("--output", required=True, help="Path to output Intel HEX")
    parser.add_argument("--power-voltage", type=float, default=0.0, help="If > 0, power the target from the tool before readout")
    parser.add_argument("--no-writeback", action="store_true", help="Only dump the MCU to HEX; do not program the dumped file back")
    parser.add_argument("--verify-writeback", action="store_true")
    parser.add_argument("--trace-output", default="", help="If set, record the RI4 packet trace and write a JSON result payload to this path")
    args = parser.parse_args(list(argv) if argv is not None else None)

    vid = int(str(args.vid), 0)
    pid = int(str(args.pid), 0) if str(args.pid).strip() else _discover_pid(vid)
    start_address = int(str(args.start_address), 0)
    length = int(str(args.length), 0)
    output_path = str(Path(args.output))
    scripts_path = str(args.scripts).strip() or None
    if scripts_path is None:
        resolved = resolve_repo_scripts_path(str(args.tool))
        if resolved is None:
            raise SystemExit("No scripts.xml was provided and no vendored repo asset is available. Run mchp-ri4-collect-assets first or pass --scripts.")
        scripts_path = str(resolved)

    power_result = None
    if float(args.power_voltage) > 0:
        driver = _open_driver(str(args.tool), vid, pid)
        try:
            power_result = driver.power_target(int(round(float(args.power_voltage) * 1000.0)))
        finally:
            driver.close()

    trace_output_path = str(args.trace_output).strip()
    session, trace_transport = _open_session(
        tool=str(args.tool),
        processor=str(args.processor),
        vid=vid,
        pid=pid,
        scripts_path=scripts_path,
        tool_scripts_path=str(args.tool_scripts).strip() or None,
        script_suffix=str(args.script_suffix).strip() or None,
        pc_bytes=int(args.pc_bytes),
        family=str(args.family),
        enable_trace=bool(trace_output_path),
    )

    try:
        payload = {
            "tool": str(args.tool).upper(),
            "vid": f"0x{vid:04X}",
            "pid": f"0x{pid:04X}",
            "family": str(args.family).strip().upper(),
            "processor": str(args.processor),
            "power": power_result,
        }
        try:
            dump_result = session.dump_program_hex(
                output_path,
                start_address=start_address,
                length=length,
                chunk_size=int(args.chunk_size),
            )
            write_result = None
            if not args.no_writeback:
                write_result = session.program_hex(output_path, erase_first=True, verify=bool(args.verify_writeback))
            payload["dump"] = dump_result
            payload["writeBack"] = write_result
            if trace_transport is not None:
                payload["trace"] = _trace_payload(trace_transport)
                _write_trace_output(trace_output_path, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        except Exception as exc:
            if trace_transport is None:
                raise
            payload["error"] = str(exc)
            payload["errorType"] = type(exc).__name__
            payload["trace"] = _trace_payload(trace_transport)
            _write_trace_output(trace_output_path, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())