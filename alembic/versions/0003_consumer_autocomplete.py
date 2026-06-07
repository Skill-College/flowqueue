"""drop workflow consumer type + add auto_complete

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fold existing workflow consumers into webhook (same dispatch + routing_rules).
    op.execute("UPDATE consumers SET type = 'webhook' WHERE type = 'workflow'")

    op.add_column(
        "consumers",
        sa.Column("auto_complete", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Recreate the enum without 'workflow' (Postgres can't drop a label in place).
    op.execute("ALTER TYPE consumer_type RENAME TO consumer_type_old")
    op.execute("CREATE TYPE consumer_type AS ENUM ('http', 'webhook', 'sdk')")
    op.execute(
        "ALTER TABLE consumers ALTER COLUMN type TYPE consumer_type "
        "USING type::text::consumer_type"
    )
    op.execute("DROP TYPE consumer_type_old")


def downgrade() -> None:
    op.execute("ALTER TYPE consumer_type RENAME TO consumer_type_old")
    op.execute("CREATE TYPE consumer_type AS ENUM ('http', 'webhook', 'workflow', 'sdk')")
    op.execute(
        "ALTER TABLE consumers ALTER COLUMN type TYPE consumer_type "
        "USING type::text::consumer_type"
    )
    op.execute("DROP TYPE consumer_type_old")
    op.drop_column("consumers", "auto_complete")
