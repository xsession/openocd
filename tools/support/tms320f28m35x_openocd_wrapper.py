#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compatibility entrypoint for the generic C28x OpenOCD wrapper."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("c28x_openocd_wrapper.py")), run_name="__main__")
