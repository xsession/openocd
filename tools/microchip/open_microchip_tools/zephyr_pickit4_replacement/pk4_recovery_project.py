from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

from .pk4_observed_profile import (
    PK4_APP2_BASE,
    PK4_APP2_INITIAL_SP,
    PK4_APP2_RESET_VECTOR,
    PK4_APP2_WINDOW_SIZE,
    PK4_APP_BASE,
    PK4_ARCHITECTURE,
    PK4_BOOT_BASE,
    PK4_BOOT_WINDOW_SIZE,
    PK4_FAMILY,
    PK4_INITIAL_SP,
    PK4_PROFILE_NAME,
    PK4_PRIMARY_ROLE,
    PK4_RESET_VECTOR,
    PK4_SECONDARY_IDENTITY,
    PK4_SECONDARY_ROLE,
    PK4_APP_WINDOW_SIZE,
)
from .pk4_observed_session import create_pk4_observed_session


@dataclass(frozen=True)
class RecoveredSlot:
    name: str
    role: str
    identity: str
    base: int
    window_size: int
    initial_sp: int
    reset_vector: int


@dataclass(frozen=True)
class Pk4RecoveryProject:
    name: str
    source_profile: str
    target_family: str
    architecture: str
    boot: RecoveredSlot
    primary_app: RecoveredSlot
    secondary_app: RecoveredSlot

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def build_pk4_recovery_project() -> Pk4RecoveryProject:
    return Pk4RecoveryProject(
        name="pk4_cleanroom_recovery_project",
        source_profile=PK4_PROFILE_NAME,
        target_family=PK4_FAMILY,
        architecture=PK4_ARCHITECTURE,
        boot=RecoveredSlot(
            name="boot",
            role="boot strap slot",
            identity="PK4 observed boot image",
            base=PK4_BOOT_BASE,
            window_size=PK4_BOOT_WINDOW_SIZE,
            initial_sp=0,
            reset_vector=0,
        ),
        primary_app=RecoveredSlot(
            name="app",
            role=PK4_PRIMARY_ROLE,
            identity="PK4 observed primary RI4 app",
            base=PK4_APP_BASE,
            window_size=PK4_APP_WINDOW_SIZE,
            initial_sp=PK4_INITIAL_SP,
            reset_vector=PK4_RESET_VECTOR,
        ),
        secondary_app=RecoveredSlot(
            name="app2",
            role=PK4_SECONDARY_ROLE,
            identity=PK4_SECONDARY_IDENTITY,
            base=PK4_APP2_BASE,
            window_size=PK4_APP2_WINDOW_SIZE,
            initial_sp=PK4_APP2_INITIAL_SP,
            reset_vector=PK4_APP2_RESET_VECTOR,
        ),
    )


def exercise_pk4_recovery_project() -> Dict[str, object]:
    project = build_pk4_recovery_project()
    session, _probe = create_pk4_observed_session()

    try:
        session.enter_debug_mode()
        primary_write = session.write_primary_slot(0x20, b"APP!")
        secondary_write = session.write_secondary_slot(0x10, b"DAP!")
        primary_read = session.read_primary_slot(0x20, 4)
        secondary_read = session.read_secondary_slot(0x10, 4)
        return {
            "project": project.to_dict(),
            "writes": {
                "primary": primary_write,
                "secondary": secondary_write,
            },
            "reads": {
                "primary": primary_read,
                "secondary": secondary_read,
            },
            "status": {
                "profile": session.get_status_value("Probe Profile"),
                "executionSlot": session.get_status_value("Execution Slot"),
                "lastProgramRegion": session.get_status_value("Last Program Region"),
                "lastProgramRole": session.get_status_value("Last Program Role"),
            },
        }
    finally:
        session.close()