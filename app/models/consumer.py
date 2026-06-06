"""Consumer model — a subscriber on a queue (http poller, webhook, workflow, sdk)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsumerType(str, enum.Enum):
    http = "http"
    webhook = "webhook"
    workflow = "workflow"
    sdk = "sdk"


class Consumer(Base):
    __tablename__ = "consumers"
    __table_args__ = (UniqueConstraint("queue_id", "name", name="uq_consumer_queue_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ConsumerType] = mapped_column(
        Enum(ConsumerType, name="consumer_type"), nullable=False
    )
    endpoint_url: Mapped[str | None] = mapped_column(String(2048))
    routing_rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    queue: Mapped["Queue"] = relationship(back_populates="consumers")  # noqa: F821
    deliveries: Mapped[list["Delivery"]] = relationship(  # noqa: F821
        back_populates="consumer", cascade="all, delete-orphan"
    )
