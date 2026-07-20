from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Protocol


Emitter = Callable[[str], None]


class CommandBackend(Protocol):
    def run(self, args: List[str], emit: Emitter) -> int:
        """Execute a command and emit output lines.

        Return an integer error code (0 == success).
        """


@dataclass
class StubBackend:
    """In-memory backend for demos/tests.

    Supported commands:
    - PING -> emits EVENT:PONG then PONG, returns 0
    - ECHO <text...> -> emits joined text, returns 0
    - FAIL [code] -> emits failure line, returns code (default 1)

    Anything else: emits a generic acknowledgment, returns 0.
    """

    def run(self, args: List[str], emit: Emitter) -> int:
        if not args:
            emit("No command")
            return 1

        cmd = args[0].strip().upper()
        rest = args[1:]

        if cmd == "PING":
            emit("EVENT:PONG")
            emit("PONG")
            return 0

        if cmd == "ECHO":
            emit(" ".join(rest))
            return 0

        if cmd == "FAIL":
            code = 1
            if rest and rest[0].strip().isdigit():
                code = int(rest[0].strip())
            emit(f"Operation Failed ({code})")
            return code

        emit(f"ACK:{cmd}")
        return 0
