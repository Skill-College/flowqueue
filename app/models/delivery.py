"""Delivery model — one row per (message, consumer). Tracks delivery lifecycle."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Delivery(Base):
    __tablename__ = "deliveries"
    # eager_defaults: fetch server/onupdate values (updated_at) via RETURNING on
    # INSERT/UPDATE so sync pydantic serialization never triggers a lazy reload.
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        UniqueConstraint("message_id", "consumer_id", name="uq_delivery_message_consumer"),
        Index("ix_delivery_consumer_status_visible", "consumer_id", "status", "visible_after"),
        Index("ix_delivery_message", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status"),
        default=DeliveryStatus.pending,
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    visible_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_remark: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped["Message"] = relationship(back_populates="deliveries")  # noqa: F821
    consumer: Mapped["Consumer"] = relationship(back_populates="deliveries")  # noqa: F821
    # No delete cascade: delivery_logs are append-only and must outlive the delivery.
    logs: Mapped[list["DeliveryLog"]] = relationship(back_populates="delivery")  # noqa: F821
