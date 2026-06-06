"""Replay request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReplayRangeRequest(BaseModel):
    from_ts: datetime
    to_ts: datetime


class ReplaySelectedRequest(BaseModel):
    message_ids: list[uuid.UUID]


class ReplayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consumer_id: uuid.UUID
    replay_type: str
    message_ids: list[uuid.UUID] | None
    from_ts: datetime | None
    to_ts: datetime | None
    status: str
    messages_replayed: int
    error_message: str | None
    requested_at: datetime
    completed_at: datetime | None
