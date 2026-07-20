from __future__ import annotations

import os
import tempfile

from mchp_simulator import debug_backend


def _write_temp_hex(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".hex")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def test_backend_breakpoints_and_memory_read() -> None:
    debug_backend.init_session("dsPIC33EP32GP502")

    # Load 4 bytes at 0x0000.
    hex_path = _write_temp_hex(":0400000001020304F2\n:00000001FF\n")
    try:
        debug_backend.load_firmware(hex_path)
    finally:
        try:
            os.unlink(hex_path)
        except Exception:
            pass

    # Program memory read should reflect loaded bytes.
    assert debug_backend.read_memory("program", 0, 4) == "01020304"

    debug_backend.clear_breakpoints()
    debug_backend.add_breakpoint(4)
    assert debug_backend.list_breakpoints() == [4]

    # Stepping should stop at the breakpoint (PC increments by 2).
    debug_backend.run_steps(10)
    status = debug_backend.get_status()
    assert int(status["pc"]) == 4
