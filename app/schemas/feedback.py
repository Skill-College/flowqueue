"""Feedback schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.feedback import FeedbackCategory


class FeedbackCreate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    email: EmailStr
    category: FeedbackCategory = FeedbackCategory.general
    message: str = Field(min_length=1, max_length=4000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    email: str
    category: FeedbackCategory
    message: str
    user_id: uuid.UUID | None
    created_at: datetime
