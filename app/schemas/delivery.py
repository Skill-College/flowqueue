"""Delivery request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    message_id: uuid.UUID
    consumer_id: uuid.UUID
    status: str
    attempt_count: int
    visible_after: datetime
    last_remark: str | None
    metadata: dict = Field(validation_alias="meta", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime | None
    completed_at: datetime | None


class PolledDelivery(DeliveryOut):
    """Delivery returned to a polling consumer, including the message payload."""

    payload: dict
    sequence_num: int


class CompleteRequest(BaseModel):
    remark: str | None = None
    metadata: dict = Field(default_factory=dict)


class FailRequest(BaseModel):
    remark: str
    metadata: dict = Field(default_factory=dict)


class RemarkRequest(BaseModel):
    remark: str


class DeliveryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    remark: str | None
    metadata: dict = Field(validation_alias="meta", serialization_alias="metadata")
    context: dict
    created_at: datetime
