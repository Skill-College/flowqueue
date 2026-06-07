"""Feedback service — persist and list product feedback."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate


async def create_feedback(
    session: AsyncSession,
    data: FeedbackCreate,
    user_id: uuid.UUID | None = None,
) -> Feedback:
    feedback = Feedback(
        name=data.name,
        email=data.email,
        category=data.category,
        message=data.message,
        user_id=user_id,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def list_feedback(
    session: AsyncSession, limit: int, offset: int
) -> tuple[list[Feedback], int]:
    total = (await session.execute(select(func.count()).select_from(Feedback))).scalar_one()
    rows = (
        await session.execute(
            select(Feedback)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total
