"""Queue API routes (owner-scoped)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.authz import authorize_queue
from app.core.security import get_principal
from app.database import get_session
from app.models.user import User
from app.schemas.common import Page
from app.schemas.queue import QueueCreate, QueueOut, QueueStats, QueueUpdate
from app.services import queue_service

router = APIRouter(prefix="/queues", tags=["queues"])

Principal = Annotated[User, Depends(get_principal)]


@router.post("", response_model=QueueOut, status_code=status.HTTP_201_CREATED)
async def create_queue(
    data: QueueCreate, user: Principal, session: AsyncSession = Depends(get_session)
):
    return await queue_service.create_queue(session, data, owner_id=user.id)


@router.get("", response_model=Page[QueueOut])
async def list_queues(
    user: Principal,
    page: Pagination = Depends(),
    archived: bool = Query(default=False, description="List archived (inactive) queues"),
    session: AsyncSession = Depends(get_session),
):
    # Admin sees all (owner_id=None filter); regular users see only their own.
    owner_id = None if user.is_admin else user.id
    items, total = await queue_service.list_queues(
        session, page.limit, page.offset, owner_id, is_active=not archived
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{queue_id}", response_model=QueueOut)
async def get_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    return await authorize_queue(session, queue_id, user)


@router.patch("/{queue_id}", response_model=QueueOut)
async def update_queue(
    queue_id: uuid.UUID,
    data: QueueUpdate,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_queue(session, queue_id, user)
    return await queue_service.update_queue(session, queue_id, data)


@router.delete("/{queue_id}", response_model=QueueOut)
async def delete_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    return await queue_service.soft_delete_queue(session, queue_id)


@router.get("/{queue_id}/stats", response_model=QueueStats)
async def get_queue_stats(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    return await queue_service.queue_stats(session, queue_id)


@router.post("/{queue_id}/pause", response_model=QueueOut)
async def pause_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    return await queue_service.set_paused(session, queue_id, True)


@router.post("/{queue_id}/resume", response_model=QueueOut)
async def resume_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    return await queue_service.set_paused(session, queue_id, False)
