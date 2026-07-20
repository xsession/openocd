from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .commands import Commands
from .device_file import DeviceFile
from .icd4_comms_usb import ICD4CommsUsb
from .named_session import NamedScriptSession
from .power_cli import _discover_pid
from .repo_assets import resolve_repo_scripts_path
from .ri4_com import Ri4Com
from .transport import PyusbTransport, ToolTransport


@dataclass
class TraceEntry:
    direction: str
    endpoint: str
    length: int
    timeoutMs: int
    dataHex: str
    header: Optional[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        result = {
            "direction": self.direction,
            "endpoint": self.endpoint,
            "length": self.length,
            "timeoutMs": self.timeoutMs,
            "dataHex": self.dataHex,
        }
        if self.header is not None:
            result["header"] = self.header
        return result


def _u32le(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        return 0
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


def _decode_header(data: bytes) -> Optional[dict[str, str]]:
    if len(data) < 16:
        return None
    return {
        "messageType": f"0x{_u32le(data, 0):08X}",
        "job": f"0x{_u32le(data, 4):08X}",
        "byteCount": str(_u32le(data, 8)),
        "transferLength": str(_u32le(data, 12)),
    }


class TracingTransport(ToolTransport):
    def __init__(self, inner: ToolTransport):
        self._inner = inner
        self.trace: list[TraceEntry] = []

    def send(self, endpoint: int, data: bytes, timeout_ms: int) -> None:
        self.trace.append(
            TraceEntry(
                direction="out",
                endpoint=f"0x{endpoint:02X}",
                length=len(data),
                timeoutMs=timeout_ms,
                dataHex=data.hex(),
                header=_decode_header(data),
            )
        )
        self._inner.send(endpoint, data, timeout_ms)

    def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
        data = self._inner.recv(endpoint, length, timeout_ms)
        self.trace.append(
            TraceEntry(
                direction="in",
                endpoint=f"0x{endpoint:02X}",
                length=len(data),
                timeoutMs=timeout_ms,
                dataHex=data.hex(),
                header=_decode_header(data),
            )
        )
        return data

    def close(self) -> None:
        self._inner.close()


def _parse_param(token: str) -> Any:
    lowered = token.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if token.startswith("bool:"):
        value = token[5:].strip().lower()
        if value not in ("true", "false"):
            raise ValueError(f"Invalid bool parameter: {token}")
        return value == "true"
    if token.startswith("str:"):
        return token[4:]
    if token.startswith("hex:"):
        return bytes.fromhex(token[4:])
    if token.startswith("bytes:"):
        return token[6:].encode("utf-8")
    try:
        return int(token, 0)
    except ValueError:
        return token


def _resolve_scripts_path(tool: str, processor: str, family: Optional[str], scripts_path: str) -> str:
    if scripts_path.strip():
        return scripts_path
    _ = processor
    _ = family
    repo_path = resolve_repo_scripts_path(tool.upper())
    if repo_path is None:
        raise RuntimeError("No scripts path was provided and no vendored repo asset could be resolved.")
    return str(repo_path)


def _result_with_trace(trace: list[TraceEntry], **payload: Any) -> dict[str, Any]:
    payload["trace"] = [entry.to_dict() for entry in trace]
    return payload


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a single RI4 side-channel diagnostic command or named script and print the exact USB packet trace"
    )
    parser.add_argument("--tool", choices=("pk4", "icd4"), default="pk4")
    parser.add_argument("--vid", default="0x04D8")
    parser.add_argument("--pid", default="")
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    subparsers = parser.add_subparsers(dest="command", required=True)

    progress_parser = subparsers.add_parser("progress", help="Send the raw RI4 progress/status command")
    progress_parser.set_defaults(action="progress")

    status_key_parser = subparsers.add_parser("status-key", help="Query one RI4 status key")
    status_key_parser.add_argument("--key", required=True)
    status_key_parser.set_defaults(action="status-key")

    raw_parser = subparsers.add_parser("raw-command", help="Send a raw side-channel command payload as hex")
    raw_parser.add_argument("--hex", required=True, dest="hex_data")
    raw_parser.add_argument("--response-length", type=int, default=1024)
    raw_parser.set_defaults(action="raw-command")

    script_parser = subparsers.add_parser("named-script", help="Load a named script and run it once")
    script_parser.add_argument("--processor", required=True)
    script_parser.add_argument("--family", default="")
    script_parser.add_argument("--scripts", default="")
    script_parser.add_argument("--script-name", required=True)
    script_parser.add_argument("--param", action="append", default=[])
    script_parser.add_argument("--upload-length", type=int, default=-1)
    script_parser.set_defaults(action="named-script")

    sequence_parser = subparsers.add_parser("script-sequence", help="Run multiple named scripts over one USB session")
    sequence_parser.add_argument("--processor", required=True)
    sequence_parser.add_argument("--family", default="")
    sequence_parser.add_argument("--scripts", default="")
    sequence_parser.add_argument("--script-name", action="append", required=True)
    sequence_parser.add_argument("--upload-script-name", default="")
    sequence_parser.add_argument("--upload-length", type=int, default=-1)
    sequence_parser.add_argument("--upload-param", action="append", default=[])
    sequence_parser.set_defaults(action="script-sequence")

    args = parser.parse_args(list(argv) if argv is not None else None)

    vid = int(str(args.vid), 0)
    pid = int(str(args.pid), 0) if str(args.pid).strip() else _discover_pid(vid)
    tool = str(args.tool).upper()

    tracing_transport = TracingTransport(PyusbTransport(vid=vid, pid=pid))
    comm = ICD4CommsUsb(Ri4Com(tracing_transport))
    try:
        if args.action == "progress":
            response = comm.get_status()
            result = _result_with_trace(
                tracing_transport.trace,
                tool=tool,
                vid=f"0x{vid:04X}",
                pid=f"0x{pid:04X}",
                command="progress",
                responseHex=response.hex(),
            )
        elif args.action == "status-key":
            value = comm.get_status_value_from_key(str(args.key))
            result = _result_with_trace(
                tracing_transport.trace,
                tool=tool,
                vid=f"0x{vid:04X}",
                pid=f"0x{pid:04X}",
                command="status-key",
                key=str(args.key),
                value=value,
            )
        elif args.action == "raw-command":
            response = comm.exec_command(bytes.fromhex(str(args.hex_data)), int(args.response_length), timeout_ms=int(args.timeout_ms))
            result = _result_with_trace(
                tracing_transport.trace,
                tool=tool,
                vid=f"0x{vid:04X}",
                pid=f"0x{pid:04X}",
                command="raw-command",
                requestHex=str(args.hex_data).replace(" ", ""),
                responseHex=response.hex(),
            )
        elif args.action == "named-script":
            scripts_path = _resolve_scripts_path(str(args.tool), str(args.processor), str(args.family) or None, str(args.scripts))
            session = NamedScriptSession(
                commands=Commands(comm),
                device_file=DeviceFile.from_xml_path(str(args.processor), scripts_path),
                tool=tool,
                processor=str(args.processor),
                vid=vid,
                pid=pid,
                family=str(args.family).strip().upper() if str(args.family).strip() else None,
            )
            try:
                params = tuple(_parse_param(token) for token in args.param)
                if int(args.upload_length) >= 0:
                    data = session.run_script_with_upload(str(args.script_name), int(args.upload_length), *params)
                    script_result: dict[str, Any] = {
                        "script": str(args.script_name),
                        "uploadLength": int(args.upload_length),
                        "dataHex": data.hex(),
                    }
                else:
                    script_result = session.run_script(str(args.script_name), *params, timeout_ms=int(args.timeout_ms))
                result = _result_with_trace(
                    tracing_transport.trace,
                    tool=tool,
                    vid=f"0x{vid:04X}",
                    pid=f"0x{pid:04X}",
                    command="named-script",
                    processor=str(args.processor),
                    family=str(args.family).strip().upper(),
                    scriptsPath=scripts_path,
                    result=script_result,
                )
            finally:
                session.close()
        else:
            scripts_path = _resolve_scripts_path(str(args.tool), str(args.processor), str(args.family) or None, str(args.scripts))
            session = NamedScriptSession(
                commands=Commands(comm),
                device_file=DeviceFile.from_xml_path(str(args.processor), scripts_path),
                tool=tool,
                processor=str(args.processor),
                vid=vid,
                pid=pid,
                family=str(args.family).strip().upper() if str(args.family).strip() else None,
            )
            try:
                steps: list[dict[str, Any]] = []
                for script_name in args.script_name:
                    steps.append(session.run_script(str(script_name), timeout_ms=int(args.timeout_ms)))
                upload_result: Optional[dict[str, Any]] = None
                if str(args.upload_script_name).strip():
                    upload_params = tuple(_parse_param(token) for token in args.upload_param)
                    data = session.run_script_with_upload(
                        str(args.upload_script_name),
                        int(args.upload_length),
                        *upload_params,
                    )
                    upload_result = {
                        "script": str(args.upload_script_name),
                        "uploadLength": int(args.upload_length),
                        "dataHex": data.hex(),
                    }
                result = _result_with_trace(
                    tracing_transport.trace,
                    tool=tool,
                    vid=f"0x{vid:04X}",
                    pid=f"0x{pid:04X}",
                    command="script-sequence",
                    processor=str(args.processor),
                    family=str(args.family).strip().upper(),
                    scriptsPath=scripts_path,
                    result=steps,
                    uploadResult=upload_result,
                )
            finally:
                session.close()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error_result = _result_with_trace(
            tracing_transport.trace,
            tool=tool,
            vid=f"0x{vid:04X}",
            pid=f"0x{pid:04X}",
            command=str(args.command),
            errorType=type(exc).__name__,
            error=str(exc),
        )
        print(json.dumps(error_result, indent=2, sort_keys=True))
        return 1
    finally:
        tracing_transport.close()


if __name__ == "__main__":
    raise SystemExit(main())