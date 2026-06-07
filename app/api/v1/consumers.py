"""Consumer API routes (nested under a queue, owner-scoped)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.api.deps import Pagination
from app.core.authz import authorize_consumer, authorize_queue
from app.core.exceptions import ConflictError
from app.core.security import get_principal
from app.database import get_session
from app.models.consumer import ConsumerType
from app.models.user import User
from app.schemas.common import Page
from app.schemas.consumer import ConsumerCreate, ConsumerOut, ConsumerUpdate
from app.services import consumer_service, webhook_service

router = APIRouter(prefix="/queues/{queue_id}/consumers", tags=["consumers"])

Principal = Annotated[User, Depends(get_principal)]


@router.post("", response_model=ConsumerOut, status_code=status.HTTP_201_CREATED)
async def create_consumer(
    queue_id: uuid.UUID,
    data: ConsumerCreate,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_queue(session, queue_id, user)
    return await consumer_service.create_consumer(session, queue_id, data)


@router.get("", response_model=Page[ConsumerOut])
async def list_consumers(
    queue_id: uuid.UUID,
    user: Principal,
    page: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
):
    await authorize_queue(session, queue_id, user)
    items, total = await consumer_service.list_consumers(
        session, queue_id, page.limit, page.offset
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{consumer_id}", response_model=ConsumerOut)
async def get_consumer(
    queue_id: uuid.UUID,
    consumer_id: uuid.UUID,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    return await authorize_consumer(session, consumer_id, user)


@router.patch("/{consumer_id}", response_model=ConsumerOut)
async def update_consumer(
    queue_id: uuid.UUID,
    consumer_id: uuid.UUID,
    data: ConsumerUpdate,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    return await consumer_service.update_consumer(session, consumer_id, data)


@router.delete("/{consumer_id}", response_model=ConsumerOut)
async def deactivate_consumer(
    queue_id: uuid.UUID,
    consumer_id: uuid.UUID,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    return await consumer_service.deactivate_consumer(session, consumer_id)


@router.post("/{consumer_id}/test")
async def test_consumer(
    queue_id: uuid.UUID,
    consumer_id: uuid.UUID,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    """Send a sample event to a webhook consumer's endpoint (wiring check)."""
    consumer = await authorize_consumer(session, consumer_id, user)
    if consumer.type != ConsumerType.webhook:
        raise ConflictError("Only webhook consumers can be tested")
    async with httpx.AsyncClient() as client:
        result = await webhook_service.send_test(client, consumer)
    return {
        "success": result.success,
        "status_code": result.status_code,
        "target_url": result.target_url,
        "detail": result.detail,
    }
