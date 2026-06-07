"""API key schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


Scope = Field(default_factory=lambda: ["publish", "consume", "admin"])


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Scope


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    """Returned only once at creation — includes the raw token."""

    token: str
