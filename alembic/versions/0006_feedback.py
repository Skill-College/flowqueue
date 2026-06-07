"""feedback table for public product feedback

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    feedback_category = postgresql.ENUM(
        "bug", "feature", "general", name="feedback_category"
    )
    feedback_category.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "bug", "feature", "general", name="feedback_category", create_type=False
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    postgresql.ENUM(name="feedback_category").drop(op.get_bind(), checkfirst=True)
