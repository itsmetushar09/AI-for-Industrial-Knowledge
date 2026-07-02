"""Stable database enum values."""

from enum import StrEnum


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    PLANT_MANAGER = "plant_manager"
    MAINTENANCE_ENGINEER = "maintenance_engineer"
    SAFETY_OFFICER = "safety_officer"
    OPERATOR = "operator"


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EquipmentStatus(StrEnum):
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    DECOMMISSIONED = "decommissioned"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum values instead of Python member names."""

    return [member.value for member in enum_class]

