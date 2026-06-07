"""Consumer service — CRUD with SSRF validation on push endpoints.

Does not write delivery_logs (operates on consumers, not deliveries).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import validate_endpoint_url
from app.models.consumer import Consumer, ConsumerType
from app.schemas.consumer import ConsumerCreate, ConsumerUpdate
from app.services.queue_service import get_queue

_PUSH_TYPES = (ConsumerType.webhook,)


def _validate_endpoint(endpoint_url) -> None:
    """SSRF-check the single webhook endpoint URL (rules are filters, not URLs)."""
    if endpoint_url:
        validate_endpoint_url(endpoint_url)


async def create_consumer(
    session: AsyncSession, queue_id: uuid.UUID, data: ConsumerCreate
) -> Consumer:
    """Create a consumer on a queue. Validates endpoint/rule URLs for SSRF."""
    await get_queue(session, queue_id)
    rules = [r.model_dump() for r in data.routing_rules]
    _validate_endpoint(data.endpoint_url)

    consumer = Consumer(
        queue_id=queue_id,
        name=data.name,
        type=data.type,
        endpoint_url=data.endpoint_url,
        routing_rules=rules,
        match_mode=data.match_mode,
        auto_complete=data.auto_complete,
        signing_secret=data.signing_secret,
        meta=data.metadata,
    )
    session.add(consumer)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(f"Consumer name already exists on queue: {data.name}") from exc
    return consumer


async def get_consumer(session: AsyncSession, consumer_id: uuid.UUID) -> Consumer:
    consumer = await session.get(Consumer, consumer_id)
    if consumer is None:
        raise NotFoundError(f"Consumer not found: {consumer_id}")
    return consumer


async def list_consumers(
    session: AsyncSession, queue_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[Consumer], int]:
    await get_queue(session, queue_id)
    total = (
        await session.execute(
            select(func.count()).select_from(Consumer).where(Consumer.queue_id == queue_id)
        )
    ).scalar_one()
    rows = (
        await session.execute(
            select(Consumer)
            .where(Consumer.queue_id == queue_id)
            .order_by(Consumer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def update_consumer(
    session: AsyncSession, consumer_id: uuid.UUID, data: ConsumerUpdate
) -> Consumer:
    consumer = await get_consumer(session, consumer_id)
    payload = data.model_dump(exclude_unset=True)

    if "routing_rules" in payload and payload["routing_rules"] is not None:
        payload["routing_rules"] = [
            r.model_dump() if hasattr(r, "model_dump") else r for r in data.routing_rules
        ]
    new_endpoint = payload.get("endpoint_url", consumer.endpoint_url)
    _validate_endpoint(new_endpoint)

    if "metadata" in payload:
        consumer.meta = payload.pop("metadata")
    for field, value in payload.items():
        setattr(consumer, field, value)
    await session.flush()
    return consumer


async def deactivate_consumer(session: AsyncSession, consumer_id: uuid.UUID) -> Consumer:
    consumer = await get_consumer(session, consumer_id)
    consumer.is_active = False
    await session.flush()
    return consumer
