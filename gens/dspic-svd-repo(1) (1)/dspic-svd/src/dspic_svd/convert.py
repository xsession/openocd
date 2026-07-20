from __future__ import annotations

from pathlib import Path

from .atdf import parse_atdf
from .edc import parse_edc
from .model import Device
from .writer import write_device


def parse_source(path: Path, device_name: str | None = None) -> Device:
    suffix = path.suffix.lower()
    if suffix == ".atdf":
        return parse_atdf(path, device_name)
    if suffix == ".pic":
        return parse_edc(path, device_name)
    raise ValueError(f"Unsupported source format: {path}")


def convert_file(source: Path, output: Path, device_name: str | None = None) -> Device:
    device = parse_source(source, device_name)
    write_device(device, output)
    return device
