#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compatibility entrypoint for the generic C28x OpenOCD wrapper."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    wrapper = Path(__file__).resolve().parents[1] / "debug-servers" / "ti" / "c2000" / "c28x_openocd_wrapper.py"
    runpy.run_path(str(wrapper), run_name="__main__")
