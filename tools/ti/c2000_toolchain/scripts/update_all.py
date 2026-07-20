#!/usr/bin/env python3
from ti_svd.cli import main

raise SystemExit(main(["generate-all", *__import__("sys").argv[1:]]))
