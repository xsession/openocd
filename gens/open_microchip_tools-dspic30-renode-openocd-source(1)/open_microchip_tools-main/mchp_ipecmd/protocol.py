from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


DELIMITER = "#"
ERROR_PREFIX = "ERRORCODE:"
SUCCESS_LINE = "Operation Succeeded"


def encode_args(args: Sequence[str]) -> str:
    """Encode command arguments into the single-line wire format."""
    return DELIMITER.join(str(a) for a in args)


def decode_line(line: str) -> List[str]:
    """Decode the single-line wire format into command arguments."""
    line = line.rstrip("\r\n")
    if not line:
        return []
    return line.split(DELIMITER)


@dataclass(frozen=True)
class IpecmdResult:
    lines: List[str]
    error_code: int
