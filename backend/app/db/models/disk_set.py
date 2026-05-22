from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.disk import DiskModel


class DiskSetModel(Base):
    __tablename__ = "disk_sets"
    __table_args__ = (Index("ix_disk_sets_slug", "slug", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    alphabet: Mapped[str] = mapped_column(
        String(26),
        nullable=False,
        default="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        server_default=text("'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        # SQLAlchemy infers the DB type from the annotation here.
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        # Keep the column server-populated and update it on row changes.
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    disks: Mapped[list[DiskModel]] = relationship(
        back_populates="disk_set",
        cascade="all, delete-orphan",
        order_by="DiskModel.position",
    )
