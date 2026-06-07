"""Queue request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    fifo_enabled: bool = False
    max_retries: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=60, ge=0)
    retention_seconds: int = Field(default=604800, ge=1)
    processed_retention_seconds: int = Field(default=2592000, ge=1)
    visibility_timeout_seconds: int = Field(default=30, ge=1)
    dlq_enabled: bool = True
    metadata: dict = Field(default_factory=dict)


class QueueUpdate(BaseModel):
    fifo_enabled: bool | None = None
    max_retries: int | None = Field(default=None, ge=0)
    retry_delay_seconds: int | None = Field(default=None, ge=0)
    retention_seconds: int | None = Field(default=None, ge=1)
    processed_retention_seconds: int | None = Field(default=None, ge=1)
    visibility_timeout_seconds: int | None = Field(default=None, ge=1)
    dlq_enabled: bool | None = None
    is_paused: bool | None = None
    metadata: dict | None = None
    is_active: bool | None = None


class QueueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID | None = None
    fifo_enabled: bool
    max_retries: int
    retry_delay_seconds: int
    retention_seconds: int
    processed_retention_seconds: int
    visibility_timeout_seconds: int
    dlq_enabled: bool
    is_paused: bool
    metadata: dict = Field(validation_alias="meta", serialization_alias="metadata")
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class QueueStats(BaseModel):
    queue_id: uuid.UUID
    pending: int
    processing: int
    completed: int
    failed: int
    total_messages: int
    consumer_count: int
    # max lag = oldest pending delivery age (seconds) across consumers
    max_consumer_lag_seconds: float | None
