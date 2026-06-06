"""DeliveryLog model — APPEND-ONLY audit trail. Never UPDATE, never DELETE.

Every delivery state transition writes one row here in the SAME transaction.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Allowed event_type values:
#   created, acknowledged, status_updated, retry_scheduled,
#   replayed, remark_added, metadata_updated, expired


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"
    __table_args__ = (
        Index("ix_delivery_logs_delivery_created", "delivery_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable + ON DELETE SET NULL: when retention purges an expired delivery,
    # its audit rows SURVIVE (logs are append-only, never deleted by us); only the
    # pointer is cleared. The log body (statuses, remark, context) preserves the trail.
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    delivery: Mapped["Delivery"] = relationship(back_populates="logs")  # noqa: F821
