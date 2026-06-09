"""QueueLog model — APPEND-ONLY queue activity timeline. Never UPDATE, never DELETE.

Records queue-level lifecycle actions (create, update, pause, resume, archive,
restore, purge). One row per action, written in the SAME transaction as the change
via app.services.queue_audit_service. Mirrors the delivery_logs audit pattern but at
queue granularity.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Allowed action values (see app/services/queue_audit_service.py):
#   queue_created, queue_updated, queue_paused, queue_resumed,
#   queue_archived, queue_restored, queue_purged


class QueueLog(Base):
    __tablename__ = "queue_logs"
    __table_args__ = (
        Index("ix_queue_logs_queue_created", "queue_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable + ON DELETE SET NULL: the timeline survives a hard queue deletion
    # (append-only — we never delete log rows ourselves); only the pointer clears.
    queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queues.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    # Who performed the action (nullable for system/legacy actions).
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remark: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
