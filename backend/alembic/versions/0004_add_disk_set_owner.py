"""add disk set owner

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-22 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "disk_sets",
        sa.Column("owner_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_disk_sets_owner_id", "disk_sets", ["owner_id"])
    op.create_foreign_key(
        "fk_disk_sets_owner_id_users",
        "disk_sets",
        "users",
        ["owner_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_disk_sets_owner_id_users", "disk_sets", type_="foreignkey")
    op.drop_index("ix_disk_sets_owner_id", table_name="disk_sets")
    op.drop_column("disk_sets", "owner_id")
