"""Message model — an immutable published payload. payload is NEVER updated."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_queue_seq", "queue_id", "sequence_num"),
        Index("ix_messages_queue_published", "queue_id", "published_at"),
        # Partial unique idempotency index created in the migration:
        #   UNIQUE(queue_id, idempotency_key) WHERE idempotency_key IS NOT NULL
        Index(
            "uq_messages_queue_idem",
            "queue_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # IMMUTABLE
    idempotency_key: Mapped[str | None] = mapped_column(String(512))
    sequence_num: Mapped[int] = mapped_column(BigInteger, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    queue: Mapped["Queue"] = relationship(back_populates="messages")  # noqa: F821
    deliveries: Mapped[list["Delivery"]] = relationship(  # noqa: F821
        back_populates="message", cascade="all, delete-orphan"
    )
