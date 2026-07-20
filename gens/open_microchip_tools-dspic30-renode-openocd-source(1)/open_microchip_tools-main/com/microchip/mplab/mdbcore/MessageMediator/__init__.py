"""Legacy shim for `com.microchip.mplab.mdbcore.MessageMediator`.

This package provides import compatibility while delegating to the
Python-first implementation in `mchp_mdbcore`.
"""

from mchp_mdbcore.message_mediator import (  # noqa: F401
    ActionList,
    BLACK,
    Color,
    Message,
    MessageMediator,
    MessageMediatorListener,
    MessageMediatorSettings,
    NbPreferencesImpl,
    PropertiesFileImpl,
    SuppressibleMessageMemo,
)

__all__ = [
    "ActionList",
    "BLACK",
    "Color",
    "Message",
    "MessageMediator",
    "MessageMediatorListener",
    "MessageMediatorSettings",
    "NbPreferencesImpl",
    "PropertiesFileImpl",
    "SuppressibleMessageMemo",
]
