from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.disk_set import DiskSetModel


class DiskModel(Base):
    """Модель отдельного диска в составе набора (DiskSet)."""

    __tablename__ = "disks"
    __table_args__ = (
        UniqueConstraint(
            "disk_set_id",
            "position",
            name="uq_disks_disk_set_id_position",
        ),
        CheckConstraint("length(sequence) = 26", name="ck_disks_sequence_length"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    disk_set_id: Mapped[int] = mapped_column(
        ForeignKey("disk_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[str] = mapped_column(String(26), nullable=False)
    disk_set: Mapped[DiskSetModel] = relationship(back_populates="disks")
