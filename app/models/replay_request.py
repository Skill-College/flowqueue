"""ReplayRequest model — a background job that re-delivers existing messages."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReplayType(str, enum.Enum):
    failed_only = "failed_only"
    selected = "selected"
    date_range = "date_range"
    full_backfill = "full_backfill"


class ReplayStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ReplayRequest(Base):
    __tablename__ = "replay_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False
    )
    replay_type: Mapped[ReplayType] = mapped_column(
        Enum(ReplayType, name="replay_type"), nullable=False
    )
    message_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    from_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    to_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReplayStatus] = mapped_column(
        Enum(ReplayStatus, name="replay_status"),
        default=ReplayStatus.pending,
        nullable=False,
    )
    messages_replayed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
