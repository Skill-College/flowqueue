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

_PUSH_TYPES = (ConsumerType.webhook, ConsumerType.workflow)


def _validate_rules_and_endpoint(consumer_type: ConsumerType, endpoint_url, rules) -> None:
    """SSRF-check the endpoint URL and every routing rule action_url."""
    if endpoint_url:
        validate_endpoint_url(endpoint_url)
    for rule in rules or []:
        action_url = rule["action_url"] if isinstance(rule, dict) else rule.action_url
        if action_url:
            validate_endpoint_url(action_url)


async def create_consumer(
    session: AsyncSession, queue_id: uuid.UUID, data: ConsumerCreate
) -> Consumer:
    """Create a consumer on a queue. Validates endpoint/rule URLs for SSRF."""
    await get_queue(session, queue_id)
    rules = [r.model_dump() for r in data.routing_rules]
    _validate_rules_and_endpoint(data.type, data.endpoint_url, rules)

    consumer = Consumer(
        queue_id=queue_id,
        name=data.name,
        type=data.type,
        endpoint_url=data.endpoint_url,
        routing_rules=rules,
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
    new_rules = payload.get("routing_rules", consumer.routing_rules)
    _validate_rules_and_endpoint(consumer.type, new_endpoint, new_rules)

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
