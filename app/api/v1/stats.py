"""Stats & cross-entity search routes (owner-scoped)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.authz import authorize_queue
from app.core.security import get_principal
from app.database import get_session
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.models.queue import Queue
from app.models.user import User
from app.schemas.common import Page
from app.schemas.delivery import DeliveryOut
from app.schemas.message import MessageOut

router = APIRouter(prefix="/search", tags=["search"])

Principal = Annotated[User, Depends(get_principal)]


@router.get("/messages", response_model=Page[MessageOut])
async def search_messages(
    user: Principal,
    page: Pagination = Depends(),
    queue_id: uuid.UUID | None = Query(default=None),
    status: DeliveryStatus | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Search the caller's messages. `status` filters to messages with at least one
    delivery in that status. `from`/`to` filter published_at. Admins see all.
    """
    # If a specific queue is requested, authorize it (404 if not owned/admin).
    if queue_id is not None:
        await authorize_queue(session, queue_id, user)
    # Restrict to owned queues (join queues, filter owner) unless admin.
    stmt = select(Message).join(Queue, Queue.id == Message.queue_id)
    count_stmt = (
        select(func.count(distinct(Message.id)))
        .select_from(Message)
        .join(Queue, Queue.id == Message.queue_id)
    )
    if not user.is_admin:
        stmt = stmt.where(Queue.owner_id == user.id)
        count_stmt = count_stmt.where(Queue.owner_id == user.id)
    if status is not None:
        stmt = stmt.join(Delivery, Delivery.message_id == Message.id).where(
            Delivery.status == status
        ).distinct()
        count_stmt = count_stmt.join(Delivery, Delivery.message_id == Message.id).where(
            Delivery.status == status
        )
    if queue_id is not None:
        stmt = stmt.where(Message.queue_id == queue_id)
        count_stmt = count_stmt.where(Message.queue_id == queue_id)
    if from_ is not None:
        stmt = stmt.where(Message.published_at >= from_)
        count_stmt = count_stmt.where(Message.published_at >= from_)
    if to is not None:
        stmt = stmt.where(Message.published_at <= to)
        count_stmt = count_stmt.where(Message.published_at <= to)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(Message.published_at.desc()).limit(page.limit).offset(page.offset)
        )
    ).scalars().all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.get("/deliveries", response_model=Page[DeliveryOut])
async def search_deliveries(
    user: Principal,
    page: Pagination = Depends(),
    consumer_id: uuid.UUID | None = Query(default=None),
    status: DeliveryStatus | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Search the caller's deliveries (joined message → queue owner). Admins see all."""
    stmt = (
        select(Delivery)
        .join(Message, Message.id == Delivery.message_id)
        .join(Queue, Queue.id == Message.queue_id)
    )
    count_stmt = (
        select(func.count())
        .select_from(Delivery)
        .join(Message, Message.id == Delivery.message_id)
        .join(Queue, Queue.id == Message.queue_id)
    )
    if not user.is_admin:
        stmt = stmt.where(Queue.owner_id == user.id)
        count_stmt = count_stmt.where(Queue.owner_id == user.id)
    if consumer_id is not None:
        stmt = stmt.where(Delivery.consumer_id == consumer_id)
        count_stmt = count_stmt.where(Delivery.consumer_id == consumer_id)
    if status is not None:
        stmt = stmt.where(Delivery.status == status)
        count_stmt = count_stmt.where(Delivery.status == status)
    if from_ is not None:
        stmt = stmt.where(Delivery.created_at >= from_)
        count_stmt = count_stmt.where(Delivery.created_at >= from_)
    if to is not None:
        stmt = stmt.where(Delivery.created_at <= to)
        count_stmt = count_stmt.where(Delivery.created_at <= to)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(Delivery.created_at.desc()).limit(page.limit).offset(page.offset)
        )
    ).scalars().all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)
