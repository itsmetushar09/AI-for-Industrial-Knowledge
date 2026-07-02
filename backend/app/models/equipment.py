"""Industrial equipment registry model."""

import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import EquipmentStatus, enum_values


class Equipment(TimestampMixin, Base):
    """A physical asset associated with an owning department."""

    __tablename__ = "equipment"
    __table_args__ = (Index("ix_equipment_department_status", "department_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    equipment_type: Mapped[str] = mapped_column(String(120), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus, name="equipment_status", values_callable=enum_values),
        nullable=False,
        default=EquipmentStatus.OPERATIONAL,
        server_default=EquipmentStatus.OPERATIONAL.value,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

