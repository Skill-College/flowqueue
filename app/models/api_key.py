"""ApiKey model — bcrypt-hashed bearer tokens for API authentication."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Owning user. The key authenticates AS this user (its queues only).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # bcrypt hash of the raw token. Raw token shown to user only once at creation.
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Short non-secret prefix to allow fast lookup without scanning every row.
    prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    # Allowed scopes: subset of {publish, consume, admin}. JWT users get all scopes.
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{publish,consume,admin}'")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
