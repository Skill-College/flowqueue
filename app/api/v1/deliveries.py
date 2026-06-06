"""Delivery API routes — poll/ack/complete/fail/history and consumer listings."""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import get_current_api_key
from app.database import get_session
from app.models.delivery import DeliveryStatus
from app.schemas.common import Page
from app.schemas.delivery import (
    CompleteRequest,
    DeliveryLogOut,
    DeliveryOut,
    FailRequest,
    PolledDelivery,
    RemarkRequest,
)
from app.services import delivery_service

router = APIRouter(tags=["deliveries"], dependencies=[Depends(get_current_api_key)])


@router.post("/consumers/{consumer_id}/poll", response_model=PolledDelivery | None)
async def poll(
    consumer_id: uuid.UUID, response: Response, session: AsyncSession = Depends(get_session)
):
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
    page: Pagination = Depends(),
    status_filter: DeliveryStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    items, total = await delivery_service.list_consumer_deliveries(
        session, consumer_id, status_filter, page.limit, page.offset
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/deliveries/{delivery_id}/ack", response_model=DeliveryOut)
async def ack(delivery_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await delivery_service.ack(session, delivery_id)


@router.post("/deliveries/{delivery_id}/complete", response_model=DeliveryOut)
async def complete(
    delivery_id: uuid.UUID,
    body: CompleteRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    body = body or CompleteRequest()
    return await delivery_service.complete(session, delivery_id, body.remark, body.metadata)


@router.post("/deliveries/{delivery_id}/fail", response_model=DeliveryOut)
async def fail(
    delivery_id: uuid.UUID,
    body: FailRequest,
    session: AsyncSession = Depends(get_session),
):
    return await delivery_service.fail(session, delivery_id, body.remark, body.metadata)


@router.post("/deliveries/{delivery_id}/remark", response_model=DeliveryOut)
async def add_remark(
    delivery_id: uuid.UUID,
    body: RemarkRequest,
    session: AsyncSession = Depends(get_session),
):
    return await delivery_service.add_remark(session, delivery_id, body.remark)


@router.get("/deliveries/{delivery_id}/history", response_model=list[DeliveryLogOut])
async def history(delivery_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await delivery_service.delivery_history(session, delivery_id)
