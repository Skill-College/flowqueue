"""Consumer request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consumer import ConsumerType

RoutingOperator = Literal["equals", "not_equals", "contains", "greater_than", "less_than"]


class RoutingRule(BaseModel):
    field: str
    operator: RoutingOperator
    value: object = None
    action_url: str


class ConsumerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: ConsumerType
    endpoint_url: str | None = Field(default=None, max_length=2048)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_endpoint_for_push(self) -> "ConsumerCreate":
        if self.type in (ConsumerType.webhook, ConsumerType.workflow) and not self.endpoint_url:
            raise ValueError("endpoint_url is required for webhook/workflow consumers")
        return self


class ConsumerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    endpoint_url: str | None = Field(default=None, max_length=2048)
    routing_rules: list[RoutingRule] | None = None
    metadata: dict | None = None
    is_active: bool | None = None


class ConsumerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    queue_id: uuid.UUID
    name: str
    type: ConsumerType
    endpoint_url: str | None
    routing_rules: list
    is_active: bool
    metadata: dict = Field(validation_alias="meta", serialization_alias="metadata")
    created_at: datetime
