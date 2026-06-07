"""Message request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    payload: dict
    idempotency_key: str | None = Field(default=None, max_length=512)
    # Scheduled/delayed delivery: hold until deliver_at (absolute) or now+delay_seconds.
    deliver_at: datetime | None = None
    delay_seconds: int | None = Field(default=None, ge=0)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    queue_id: uuid.UUID
    payload: dict
    idempotency_key: str | None
    sequence_num: int
    published_at: datetime
    scheduled_for: datetime | None = None
    expires_at: datetime


class DeliverySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consumer_id: uuid.UUID
    status: str
    attempt_count: int


class MessageDetail(MessageOut):
    deliveries: list[DeliverySummary] = Field(default_factory=list)
