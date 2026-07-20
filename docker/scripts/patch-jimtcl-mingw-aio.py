#!/usr/bin/env python3
"""Enable Jim Tcl AIO sockets for MinGW without disabling the AIO extension."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-jimtcl-mingw-aio.py <jimtcl-dir>")

path = Path(sys.argv[1]) / "jim-aio.c"
text = path.read_text(encoding="utf-8")

old_variants = (
    "#elif defined (__MINGW32__)\n/* currently mingw32 doesn't support sockets, but has pipe, fdopen */\n#endif",
    "#elif defined(__MINGW32__)\n/* currently mingw32 doesn't support sockets, but has pipe, fdopen */\n#endif",
)
replacement = """#elif defined(__MINGW32__)
/* MinGW provides BSD-style socket APIs through WinSock2. */
#include <winsock2.h>
#include <ws2tcpip.h>
#ifndef SHUT_RD
#define SHUT_RD SD_RECEIVE
#endif
#ifndef SHUT_WR
#define SHUT_WR SD_SEND
#endif
#define HAVE_SOCKETS
#endif"""

if replacement in text:
    print(f"Jim Tcl MinGW AIO patch already present in {path}")
    raise SystemExit(0)

for old in old_variants:
    if old in text:
        path.write_text(text.replace(old, replacement, 1), encoding="utf-8", newline="\n")
        print(f"Patched Jim Tcl MinGW AIO support in {path}")
        break
else:
    raise SystemExit(f"ERROR: expected MinGW socket block not found in {path}")
