"""Consumer request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consumer import ConsumerType

RoutingOperator = Literal["equals", "not_equals", "contains", "greater_than", "less_than"]
MatchMode = Literal["any", "all"]


class RoutingRule(BaseModel):
    """A filter condition on the webhook's payload. Not a routing target."""

    field: str
    operator: RoutingOperator
    value: object = None


class ConsumerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: ConsumerType
    endpoint_url: str | None = Field(default=None, max_length=2048)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    match_mode: MatchMode = "any"
    # Push (webhook) only. True => complete on 2xx; False => wait for callback.
    auto_complete: bool = True
    signing_secret: str | None = Field(default=None, max_length=128)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_endpoint_for_push(self) -> "ConsumerCreate":
        if self.type == ConsumerType.webhook and not self.endpoint_url:
            raise ValueError("endpoint_url is required for webhook consumers")
        return self


class ConsumerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    endpoint_url: str | None = Field(default=None, max_length=2048)
    routing_rules: list[RoutingRule] | None = None
    match_mode: MatchMode | None = None
    auto_complete: bool | None = None
    signing_secret: str | None = Field(default=None, max_length=128)
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
    match_mode: MatchMode
    auto_complete: bool
    signing_secret: str | None
    is_active: bool
    metadata: dict = Field(validation_alias="meta", serialization_alias="metadata")
    created_at: datetime
