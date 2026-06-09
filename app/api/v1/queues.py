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
from app.schemas.queue import (
    QueueCreate,
    QueueLogOut,
    QueueOut,
    QueueStats,
    QueueUpdate,
)
from app.services import queue_audit_service, queue_service

router = APIRouter(prefix="/queues", tags=["queues"])

Principal = Annotated[User, Depends(get_principal)]


@router.post("", response_model=QueueOut, status_code=status.HTTP_201_CREATED)
async def create_queue(
    data: QueueCreate, user: Principal, session: AsyncSession = Depends(get_session)
):
    queue = await queue_service.create_queue(session, data, owner_id=user.id)
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue.id,
        action=queue_audit_service.QUEUE_CREATED,
        actor_id=user.id,
        remark=f"Queue '{queue.name}' created",
    )
    return queue


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
    changed = data.model_dump(exclude_unset=True)
    queue = await queue_service.update_queue(session, queue_id, data)
    # Map common toggles to specific actions so the timeline filter is meaningful;
    # anything else is a generic config update.
    if changed.get("is_active") is True:
        action = queue_audit_service.QUEUE_RESTORED
    elif changed.get("is_paused") is True:
        action = queue_audit_service.QUEUE_PAUSED
    elif changed.get("is_paused") is False:
        action = queue_audit_service.QUEUE_RESUMED
    else:
        action = queue_audit_service.QUEUE_UPDATED
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue_id,
        action=action,
        actor_id=user.id,
        context={"changed": list(changed.keys())},
    )
    return queue


@router.delete("/{queue_id}", response_model=QueueOut)
async def delete_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    queue = await queue_service.soft_delete_queue(session, queue_id)
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue_id,
        action=queue_audit_service.QUEUE_ARCHIVED,
        actor_id=user.id,
        remark="Queue archived",
    )
    return queue


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
    queue = await queue_service.set_paused(session, queue_id, True)
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue_id,
        action=queue_audit_service.QUEUE_PAUSED,
        actor_id=user.id,
        remark="Queue paused",
    )
    return queue


@router.post("/{queue_id}/resume", response_model=QueueOut)
async def resume_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_queue(session, queue_id, user)
    queue = await queue_service.set_paused(session, queue_id, False)
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue_id,
        action=queue_audit_service.QUEUE_RESUMED,
        actor_id=user.id,
        remark="Queue resumed",
    )
    return queue


@router.post("/{queue_id}/purge")
async def purge_queue(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    """Permanently delete all pending (un-started) messages. Cannot be undone."""
    await authorize_queue(session, queue_id, user)
    counts = await queue_service.purge_queue(session, queue_id)
    queue_audit_service.write_queue_log(
        session,
        queue_id=queue_id,
        action=queue_audit_service.QUEUE_PURGED,
        actor_id=user.id,
        remark=f"Purged {counts['messages']} pending messages",
        context=counts,
    )
    return counts


@router.get("/{queue_id}/timeline", response_model=Page[QueueLogOut])
async def get_queue_timeline(
    queue_id: uuid.UUID,
    user: Principal,
    page: Pagination = Depends(),
    action: str | None = Query(default=None, description="Filter by action type"),
    session: AsyncSession = Depends(get_session),
):
    await authorize_queue(session, queue_id, user)
    items, total = await queue_audit_service.list_queue_logs(
        session, queue_id, page.limit, page.offset, action=action
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)
