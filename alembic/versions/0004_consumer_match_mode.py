"""consumer match_mode (webhook rules = filter)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consumers",
        sa.Column("match_mode", sa.String(8), nullable=False, server_default="any"),
    )


def downgrade() -> None:
    op.drop_column("consumers", "match_mode")
