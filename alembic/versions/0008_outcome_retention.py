"""outcome-based message retention

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-08

Replaces the unused queues.processed_retention_seconds with success_retention_seconds
(default 24h) and adds failed_retention_seconds (default 7d). Existing rows keep their
old processed value as the success window; new rows get the 24h default.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "queues",
        "processed_retention_seconds",
        new_column_name="success_retention_seconds",
        server_default="86400",
    )
    op.add_column(
        "queues",
        sa.Column(
            "failed_retention_seconds",
            sa.Integer(),
            nullable=False,
            server_default="604800",
        ),
    )


def downgrade() -> None:
    op.drop_column("queues", "failed_retention_seconds")
    op.alter_column(
        "queues",
        "success_retention_seconds",
        new_column_name="processed_retention_seconds",
        server_default="2592000",
    )
