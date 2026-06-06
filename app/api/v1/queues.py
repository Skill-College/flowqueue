"""Queue API routes."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import get_current_api_key
from app.database import get_session
from app.schemas.common import Page
from app.schemas.queue import QueueCreate, QueueOut, QueueStats, QueueUpdate
from app.services import queue_service

router = APIRouter(
    prefix="/queues", tags=["queues"], dependencies=[Depends(get_current_api_key)]
)


@router.post("", response_model=QueueOut, status_code=status.HTTP_201_CREATED)
async def create_queue(data: QueueCreate, session: AsyncSession = Depends(get_session)):
    return await queue_service.create_queue(session, data)


@router.get("", response_model=Page[QueueOut])
async def list_queues(
    page: Pagination = Depends(), session: AsyncSession = Depends(get_session)
):
    items, total = await queue_service.list_queues(session, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{queue_id}", response_model=QueueOut)
async def get_queue(queue_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await queue_service.get_queue(session, queue_id)


@router.patch("/{queue_id}", response_model=QueueOut)
async def update_queue(
    queue_id: uuid.UUID, data: QueueUpdate, session: AsyncSession = Depends(get_session)
):
    return await queue_service.update_queue(session, queue_id, data)


@router.delete("/{queue_id}", response_model=QueueOut)
async def delete_queue(queue_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await queue_service.soft_delete_queue(session, queue_id)


@router.get("/{queue_id}/stats", response_model=QueueStats)
async def get_queue_stats(queue_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await queue_service.queue_stats(session, queue_id)
