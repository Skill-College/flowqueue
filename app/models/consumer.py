"""Consumer model — a subscriber on a queue (http poller, webhook push, sdk)."""

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
    # Filter conditions for this webhook (field/operator/value). Not multi-URL routing.
    routing_rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # How to combine rules: 'any' (deliver if any matches) or 'all' (deliver if all).
    match_mode: Mapped[str] = mapped_column(String(8), default="any", nullable=False)
    # Optional HMAC secret; if set, outbound webhooks include X-FlowQueue-Signature.
    signing_secret: Mapped[str | None] = mapped_column(String(128))
    # Webhook (push) only: extra request headers sent on every POST so the receiver
    # can validate the call (e.g. Authorization, X-Api-Key). Reserved X-FlowQueue-*
    # and the signature header always win over these (see webhook_service._post).
    custom_headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Push (webhook) only: True => mark delivery completed on HTTP 2xx (default).
    # False => 2xx leaves it 'processing'; receiver must call complete/fail back,
    # else the visibility timeout reclaims and redelivers it.
    auto_complete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    queue: Mapped["Queue"] = relationship(back_populates="consumers")  # noqa: F821
    deliveries: Mapped[list["Delivery"]] = relationship(  # noqa: F821
        back_populates="consumer", cascade="all, delete-orphan"
    )
