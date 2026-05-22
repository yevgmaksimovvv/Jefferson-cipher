"""create disk_sets and disks

Revision ID: 0001
Revises:
Create Date: 2026-05-22 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disk_sets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column(
            "alphabet",
            sa.String(length=26),
            nullable=False,
            server_default=sa.text("'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_disk_sets_slug",
        "disk_sets",
        ["slug"],
        unique=True,
    )

    op.create_table(
        "disks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "disk_set_id",
            sa.Integer(),
            sa.ForeignKey("disk_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.String(length=26), nullable=False),
        sa.CheckConstraint("length(sequence) = 26", name="ck_disks_sequence_length"),
        sa.UniqueConstraint(
            "disk_set_id",
            "position",
            name="uq_disks_disk_set_id_position",
        ),
    )
    op.create_index("ix_disks_disk_set_id", "disks", ["disk_set_id"])


def downgrade() -> None:
    op.drop_index("ix_disks_disk_set_id", table_name="disks")
    op.drop_table("disks")
    op.drop_index("ix_disk_sets_slug", table_name="disk_sets")
    op.drop_table("disk_sets")
