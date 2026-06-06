"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("fifo_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_delay_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retention_seconds", sa.Integer(), nullable=False, server_default="604800"),
        sa.Column(
            "processed_retention_seconds", sa.Integer(), nullable=False, server_default="2592000"
        ),
        sa.Column(
            "visibility_timeout_seconds", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "queue_sequences",
        sa.Column(
            "queue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("last_value", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.create_table(
        "consumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "queue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "type",
            sa.Enum("http", "webhook", "workflow", "sdk", name="consumer_type"),
            nullable=False,
        ),
        sa.Column("endpoint_url", sa.String(2048), nullable=True),
        sa.Column("routing_rules", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("queue_id", "name", name="uq_consumer_queue_name"),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "queue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(512), nullable=True),
        sa.Column("sequence_num", sa.BigInteger(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_queue_seq", "messages", ["queue_id", "sequence_num"])
    op.create_index("ix_messages_queue_published", "messages", ["queue_id", "published_at"])
    op.create_index(
        "uq_messages_queue_idem",
        "messages",
        ["queue_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "consumer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consumers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", name="delivery_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visible_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_remark", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("message_id", "consumer_id", name="uq_delivery_message_consumer"),
    )
    op.create_index(
        "ix_delivery_consumer_status_visible",
        "deliveries",
        ["consumer_id", "status", "visible_after"],
    )
    op.create_index("ix_delivery_message", "deliveries", ["message_id"])

    op.create_table(
        "delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "delivery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deliveries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_delivery_logs_delivery_created", "delivery_logs", ["delivery_id", "created_at"]
    )

    op.create_table(
        "replay_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "consumer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consumers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "replay_type",
            sa.Enum(
                "failed_only", "selected", "date_range", "full_backfill", name="replay_type"
            ),
            nullable=False,
        ),
        sa.Column("message_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("from_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("to_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="replay_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("messages_replayed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("replay_requests")
    op.drop_table("delivery_logs")
    op.drop_table("deliveries")
    op.drop_table("messages")
    op.drop_table("consumers")
    op.drop_table("queue_sequences")
    op.drop_table("queues")
    for enum_name in (
        "replay_status",
        "replay_type",
        "delivery_status",
        "consumer_type",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
