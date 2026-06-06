"""Consumer API routes (nested under a queue)."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import get_current_api_key
from app.database import get_session
from app.schemas.common import Page
from app.schemas.consumer import ConsumerCreate, ConsumerOut, ConsumerUpdate
from app.services import consumer_service

router = APIRouter(
    prefix="/queues/{queue_id}/consumers",
    tags=["consumers"],
    dependencies=[Depends(get_current_api_key)],
)


@router.post("", response_model=ConsumerOut, status_code=status.HTTP_201_CREATED)
async def create_consumer(
    queue_id: uuid.UUID, data: ConsumerCreate, session: AsyncSession = Depends(get_session)
):
    return await consumer_service.create_consumer(session, queue_id, data)


@router.get("", response_model=Page[ConsumerOut])
async def list_consumers(
    queue_id: uuid.UUID,
    page: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
):
    items, total = await consumer_service.list_consumers(
        session, queue_id, page.limit, page.offset
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{consumer_id}", response_model=ConsumerOut)
async def get_consumer(
    queue_id: uuid.UUID, consumer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await consumer_service.get_consumer(session, consumer_id)


@router.patch("/{consumer_id}", response_model=ConsumerOut)
async def update_consumer(
    queue_id: uuid.UUID,
    consumer_id: uuid.UUID,
    data: ConsumerUpdate,
    session: AsyncSession = Depends(get_session),
):
    return await consumer_service.update_consumer(session, consumer_id, data)


@router.delete("/{consumer_id}", response_model=ConsumerOut)
async def deactivate_consumer(
    queue_id: uuid.UUID, consumer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await consumer_service.deactivate_consumer(session, consumer_id)
