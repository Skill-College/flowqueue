"""queue timeline (queue_logs) and webhook custom headers

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-08

Adds:
  * consumers.custom_headers (JSONB) — extra headers sent on webhook POSTs.
  * queue_logs table — append-only queue activity timeline.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consumers",
        sa.Column(
            "custom_headers",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
    )

    op.create_table(
        "queue_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "queue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "context",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_queue_logs_queue_created", "queue_logs", ["queue_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_queue_logs_queue_created", table_name="queue_logs")
    op.drop_table("queue_logs")
    op.drop_column("consumers", "custom_headers")
