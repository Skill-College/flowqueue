"""Queue model — a named channel that owns messages and consumers."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Queue(Base):
    __tablename__ = "queues"
    # Fetch updated_at (onupdate) via RETURNING so sync serialization never lazy-loads.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Owner of this queue. Nullable to tolerate pre-tenancy (orphan) rows; new
    # queues always set it. Isolation: a user sees only their own queues (admin all).
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    fifo_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    retention_seconds: Mapped[int] = mapped_column(
        Integer, default=604800, nullable=False
    )
    processed_retention_seconds: Mapped[int] = mapped_column(
        Integer, default=2592000, nullable=False
    )
    visibility_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    # Python attr `meta` -> DB column "metadata" (metadata is reserved on Base).
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dlq_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    consumers: Mapped[list["Consumer"]] = relationship(  # noqa: F821
        back_populates="queue", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="queue", cascade="all, delete-orphan"
    )
