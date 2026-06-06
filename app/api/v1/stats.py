"""Stats & cross-entity search routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import get_current_api_key
from app.database import get_session
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.schemas.common import Page
from app.schemas.delivery import DeliveryOut
from app.schemas.message import MessageOut

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(get_current_api_key)])


@router.get("/messages", response_model=Page[MessageOut])
async def search_messages(
    page: Pagination = Depends(),
    queue_id: uuid.UUID | None = Query(default=None),
    status: DeliveryStatus | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Search messages across queues. `status` filters to messages that have at
    least one delivery in that status. `from`/`to` filter published_at.
    """
    stmt = select(Message)
    count_stmt = select(func.count(distinct(Message.id))).select_from(Message)
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
    page: Pagination = Depends(),
    consumer_id: uuid.UUID | None = Query(default=None),
    status: DeliveryStatus | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Search deliveries, optionally by consumer, status, and created_at range."""
    filters = []
    if consumer_id is not None:
        filters.append(Delivery.consumer_id == consumer_id)
    if status is not None:
        filters.append(Delivery.status == status)
    if from_ is not None:
        filters.append(Delivery.created_at >= from_)
    if to is not None:
        filters.append(Delivery.created_at <= to)

    total = (
        await session.execute(select(func.count()).select_from(Delivery).where(*filters))
    ).scalar_one()
    rows = (
        await session.execute(
            select(Delivery)
            .where(*filters)
            .order_by(Delivery.created_at.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
    ).scalars().all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)
