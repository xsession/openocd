#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compatibility launcher for the Microchip MDB GDB facade."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    wrapper = Path(__file__).resolve().parents[1] / "debug-servers" / "microchip" / "mdb" / "mdb_gdb_wrapper.py"
    runpy.run_path(str(wrapper), run_name="__main__")
