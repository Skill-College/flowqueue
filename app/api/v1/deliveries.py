"""Delivery API routes — poll/ack/complete/fail/history and consumer listings.

All routes are owner-scoped: the principal must own the queue behind the
consumer/delivery, else 404.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.authz import authorize_consumer, authorize_delivery, authorize_queue
from app.core.security import get_principal, require_scope
from app.database import get_session
from app.models.delivery import DeliveryStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.consumer import ConsumerOut
from app.schemas.delivery import (
    CompleteRequest,
    DeliveryLogOut,
    DeliveryOut,
    FailRequest,
    PolledDelivery,
    RemarkRequest,
)
from app.services import delivery_service

router = APIRouter(tags=["deliveries"])

Principal = Annotated[User, Depends(get_principal)]


@router.get("/consumers/{consumer_id}", response_model=ConsumerOut)
async def get_consumer_by_id(
    consumer_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    """Fetch a consumer by id (owner-scoped) — convenience for the UI."""
    return await authorize_consumer(session, consumer_id, user)


@router.post("/consumers/{consumer_id}/poll", response_model=PolledDelivery | None)
async def poll(
    consumer_id: uuid.UUID,
    response: Response,
    user: Principal,
    _scope: User = Depends(require_scope("consume")),
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    result = await delivery_service.poll_next(session, consumer_id)
    if result is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    delivery = result["delivery"]
    return PolledDelivery(
        **DeliveryOut.model_validate(delivery).model_dump(),
        payload=result["payload"],
        sequence_num=result["sequence_num"],
    )


@router.get("/consumers/{consumer_id}/deliveries", response_model=Page[DeliveryOut])
async def list_consumer_deliveries(
    consumer_id: uuid.UUID,
    user: Principal,
    page: Pagination = Depends(),
    status_filter: DeliveryStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    items, total = await delivery_service.list_consumer_deliveries(
        session, consumer_id, status_filter, page.limit, page.offset
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
async def get_delivery(
    delivery_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    """Fetch a single delivery (owner-scoped)."""
    return await authorize_delivery(session, delivery_id, user)


@router.post("/deliveries/{delivery_id}/ack", response_model=DeliveryOut)
async def ack(
    delivery_id: uuid.UUID,
    user: Principal,
    _scope: User = Depends(require_scope("consume")),
    session: AsyncSession = Depends(get_session),
):
    await authorize_delivery(session, delivery_id, user)
    return await delivery_service.ack(session, delivery_id)


@router.post("/deliveries/{delivery_id}/complete", response_model=DeliveryOut)
async def complete(
    delivery_id: uuid.UUID,
    user: Principal,
    body: CompleteRequest | None = None,
    _scope: User = Depends(require_scope("consume")),
    session: AsyncSession = Depends(get_session),
):
    await authorize_delivery(session, delivery_id, user)
    body = body or CompleteRequest()
    return await delivery_service.complete(session, delivery_id, body.remark, body.metadata)


@router.post("/deliveries/{delivery_id}/fail", response_model=DeliveryOut)
async def fail(
    delivery_id: uuid.UUID,
    body: FailRequest,
    user: Principal,
    _scope: User = Depends(require_scope("consume")),
    session: AsyncSession = Depends(get_session),
):
    await authorize_delivery(session, delivery_id, user)
    return await delivery_service.fail(session, delivery_id, body.remark, body.metadata)


@router.post("/deliveries/{delivery_id}/remark", response_model=DeliveryOut)
async def add_remark(
    delivery_id: uuid.UUID,
    body: RemarkRequest,
    user: Principal,
    _scope: User = Depends(require_scope("consume")),
    session: AsyncSession = Depends(get_session),
):
    await authorize_delivery(session, delivery_id, user)
    return await delivery_service.add_remark(session, delivery_id, body.remark)


@router.get("/deliveries/{delivery_id}/history", response_model=list[DeliveryLogOut])
async def history(
    delivery_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_delivery(session, delivery_id, user)
    return await delivery_service.delivery_history(session, delivery_id)


# --------------------------------------------------------------------------- #
# Dead Letter Queue
# --------------------------------------------------------------------------- #
@router.get("/queues/{queue_id}/dlq", response_model=Page[DeliveryOut])
async def list_dlq(
    queue_id: uuid.UUID,
    user: Principal,
    page: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
):
    await authorize_queue(session, queue_id, user)
    items, total = await delivery_service.list_dlq(session, queue_id, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/deliveries/{delivery_id}/requeue", response_model=DeliveryOut)
async def requeue_delivery(
    delivery_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    delivery = await authorize_delivery(session, delivery_id, user)
    delivery_service.requeue(session, delivery)
    await session.flush()
    return delivery


@router.post("/deliveries/{delivery_id}/discard", response_model=DeliveryOut)
async def discard_delivery(
    delivery_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    delivery = await authorize_delivery(session, delivery_id, user)
    delivery_service.discard(session, delivery)
    await session.flush()
    return delivery


@router.post("/queues/{queue_id}/dlq/requeue")
async def requeue_dlq(
    queue_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    """Bulk-requeue all dead deliveries in a queue's DLQ."""
    await authorize_queue(session, queue_id, user)
    rows, _ = await delivery_service.list_dlq(session, queue_id, limit=1000, offset=0)
    for d in rows:
        delivery_service.requeue(session, d)
    await session.flush()
    return {"requeued": len(rows)}
