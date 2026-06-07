"""Message service — publishing (immutable) and querying messages.

Publish writes, in ONE transaction: the message row, one pending delivery per
active consumer, and a `created` delivery_log per delivery (via audit_service).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.consumer import Consumer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.schemas.message import MessageCreate
from app.services import audit_service
from app.services.queue_service import get_active_queue


async def _next_sequence(session: AsyncSession, queue_id: uuid.UUID) -> int:
    """Atomically increment the per-queue counter under a row lock.

    Uses SELECT ... FOR UPDATE on queue_sequences so concurrent publishers to the
    same queue get distinct, gapless, ordered sequence numbers.
    """
    row = (
        await session.execute(
            text(
                "SELECT last_value FROM queue_sequences "
                "WHERE queue_id = :qid FOR UPDATE"
            ),
            {"qid": str(queue_id)},
        )
    ).first()
    if row is None:
        # Self-heal: create the counter if missing.
        await session.execute(
            text("INSERT INTO queue_sequences (queue_id, last_value) VALUES (:qid, 0)"),
            {"qid": str(queue_id)},
        )
        last = 0
    else:
        last = row[0]
    nxt = last + 1
    await session.execute(
        text("UPDATE queue_sequences SET last_value = :v WHERE queue_id = :qid"),
        {"v": nxt, "qid": str(queue_id)},
    )
    return nxt


async def publish_message(
    session: AsyncSession, queue_id: uuid.UUID, data: MessageCreate
) -> tuple[Message, bool]:
    """Publish a message to a queue. Returns (message, created).

    Steps (all in one transaction):
      1. Validate queue exists and is active.
      2. If idempotency_key given and already used on this queue, return existing
         message with created=False (no new deliveries).
      3. Reserve next per-queue sequence_num under row lock.
      4. Insert message with computed expires_at (payload is immutable).
      5. Create one pending delivery per ACTIVE consumer.
      6. Write a `created` delivery_log for each delivery (audit_service).

    Writes to audit log: one `created` row per delivery created.
    """
    queue = await get_active_queue(session, queue_id)

    if data.idempotency_key is not None:
        existing = (
            await session.execute(
                select(Message).where(
                    Message.queue_id == queue_id,
                    Message.idempotency_key == data.idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False

    # Require at least one active consumer so messages aren't published into the void.
    active_consumers = (
        await session.execute(
            select(func.count())
            .select_from(Consumer)
            .where(Consumer.queue_id == queue_id, Consumer.is_active.is_(True))
        )
    ).scalar_one()
    if active_consumers == 0:
        raise ConflictError("Queue has no active consumers; add one before publishing")

    seq = await _next_sequence(session, queue_id)
    now = datetime.now(timezone.utc)

    # Scheduled/delayed delivery: hold until deliver_at or now+delay_seconds.
    scheduled_for: datetime | None = data.deliver_at
    if scheduled_for is None and data.delay_seconds:
        scheduled_for = now + timedelta(seconds=data.delay_seconds)
    visible_after = scheduled_for if scheduled_for and scheduled_for > now else now

    message = Message(
        queue_id=queue_id,
        payload=data.payload,
        idempotency_key=data.idempotency_key,
        sequence_num=seq,
        published_at=now,
        scheduled_for=scheduled_for,
        expires_at=now + timedelta(seconds=queue.retention_seconds),
    )
    session.add(message)
    await session.flush()

    consumers = (
        await session.execute(
            select(Consumer).where(
                Consumer.queue_id == queue_id, Consumer.is_active.is_(True)
            )
        )
    ).scalars().all()

    for consumer in consumers:
        delivery = Delivery(
            message_id=message.id,
            consumer_id=consumer.id,
            status=DeliveryStatus.pending,
            visible_after=visible_after,
        )
        session.add(delivery)
        await session.flush()  # assign delivery.id before logging
        audit_service.write_log(
            session,
            delivery_id=delivery.id,
            event_type=audit_service.EVENT_CREATED,
            to_status=DeliveryStatus.pending,
            context={"sequence_num": seq, "consumer_id": str(consumer.id)},
        )

    return message, True


async def get_message(session: AsyncSession, queue_id: uuid.UUID, message_id: uuid.UUID) -> Message:
    message = await session.get(Message, message_id)
    if message is None or message.queue_id != queue_id:
        raise NotFoundError(f"Message not found: {message_id}")
    return message


async def list_messages(
    session: AsyncSession,
    queue_id: uuid.UUID,
    limit: int,
    offset: int,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> tuple[list[Message], int]:
    """List messages on a queue, newest first, optionally filtered by published_at."""
    filters = [Message.queue_id == queue_id]
    if from_ts is not None:
        filters.append(Message.published_at >= from_ts)
    if to_ts is not None:
        filters.append(Message.published_at <= to_ts)

    total = (
        await session.execute(select(func.count()).select_from(Message).where(*filters))
    ).scalar_one()
    rows = (
        await session.execute(
            select(Message)
            .where(*filters)
            .order_by(Message.sequence_num.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total
