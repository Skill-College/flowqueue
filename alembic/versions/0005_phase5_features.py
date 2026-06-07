"""phase 5: DLQ status, pause, dlq_enabled, scheduled, signing_secret, key scopes

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'dead' to delivery_status enum (recreate to avoid ADD VALUE-in-txn limits).
    op.execute("ALTER TYPE delivery_status RENAME TO delivery_status_old")
    op.execute("CREATE TYPE delivery_status AS ENUM ('pending','processing','completed','failed','dead')")
    op.execute("ALTER TABLE deliveries ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE deliveries ALTER COLUMN status TYPE delivery_status "
        "USING status::text::delivery_status"
    )
    op.execute("ALTER TABLE deliveries ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE delivery_status_old")

    op.add_column("queues", sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("queues", sa.Column("dlq_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("messages", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consumers", sa.Column("signing_secret", sa.String(128), nullable=True))
    op.add_column(
        "api_keys",
        sa.Column(
            "scopes",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{publish,consume,admin}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "scopes")
    op.drop_column("consumers", "signing_secret")
    op.drop_column("messages", "scheduled_for")
    op.drop_column("queues", "dlq_enabled")
    op.drop_column("queues", "is_paused")
    op.execute("ALTER TYPE delivery_status RENAME TO delivery_status_old")
    op.execute("CREATE TYPE delivery_status AS ENUM ('pending','processing','completed','failed')")
    op.execute("ALTER TABLE deliveries ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE deliveries ALTER COLUMN status TYPE delivery_status "
        "USING status::text::delivery_status"
    )
    op.execute("ALTER TABLE deliveries ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE delivery_status_old")
