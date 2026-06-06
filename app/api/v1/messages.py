"""Message API routes (nested under a queue)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import get_current_api_key
from app.database import get_session
from app.schemas.common import Page
from app.schemas.message import MessageCreate, MessageDetail, MessageOut
from app.services import message_service

router = APIRouter(
    prefix="/queues/{queue_id}/messages",
    tags=["messages"],
    dependencies=[Depends(get_current_api_key)],
)


@router.post("", response_model=MessageOut)
async def publish_message(
    queue_id: uuid.UUID,
    data: MessageCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    message, created = await message_service.publish_message(session, queue_id, data)
    # 201 on new publish, 200 when an idempotent duplicate returns the existing row.
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return message


@router.get("", response_model=Page[MessageOut])
async def list_messages(
    queue_id: uuid.UUID,
    page: Pagination = Depends(),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    items, total = await message_service.list_messages(
        session, queue_id, page.limit, page.offset, from_ts, to_ts
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{message_id}", response_model=MessageDetail)
async def get_message(
    queue_id: uuid.UUID, message_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    message = await message_service.get_message(session, queue_id, message_id)
    # deliveries relationship is lazy; load explicitly for the summary.
    await session.refresh(message, attribute_names=["deliveries"])
    return message
