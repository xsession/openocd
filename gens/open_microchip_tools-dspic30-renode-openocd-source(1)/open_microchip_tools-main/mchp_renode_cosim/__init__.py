"""Renode co-simulation helpers (prototype).

This package provides the low-level wire format used by Renode's CoSimulationPlugin
and a minimal socket-based agent suitable for bring-up experiments.
"""

from .protocol import ActionType, ProtocolMessage

__all__ = ["ActionType", "ProtocolMessage"]
