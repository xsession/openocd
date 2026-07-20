"""Minimal GDB Remote Serial Protocol (RSP) client.

This speaks the same wire protocol as GNU gdb when connecting to an RSP server
(e.g. OpenOCD's `gdb_port`).
"""

from .client import GdbRemoteClient, StopReply

__all__ = [
    "GdbRemoteClient",
    "StopReply",
]
