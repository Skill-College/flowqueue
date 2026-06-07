"""Delivery service — the delivery lifecycle engine.

States: pending -> processing -> completed | failed.

AUDIT RULE: every state transition here writes a delivery_log row via
audit_service in the SAME session/transaction. No mutation bypasses that.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.consumer import Consumer, ConsumerType
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.models.queue import Queue
from app.services import audit_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_delivery(session: AsyncSession, delivery_id: uuid.UUID) -> Delivery:
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None:
        raise NotFoundError(f"Delivery not found: {delivery_id}")
    return delivery


async def _queue_for_delivery(session: AsyncSession, delivery: Delivery) -> Queue:
    queue = (
        await session.execute(
            select(Queue)
            .join(Message, Message.queue_id == Queue.id)
            .where(Message.id == delivery.message_id)
        )
    ).scalar_one()
    return queue


# --------------------------------------------------------------------------- #
# Poll (claim) — used by http / sdk consumers
# --------------------------------------------------------------------------- #
async def poll_next(session: AsyncSession, consumer_id: uuid.UUID) -> dict | None:
    """Atomically claim the next available pending delivery for a consumer.

    Selects a visible pending delivery with FOR UPDATE SKIP LOCKED (so concurrent
    pollers never get the same row), moves it to `processing`, sets the visibility
    timeout, and returns it joined with its message payload. FIFO queues order by
    sequence_num; otherwise by visible_after/created_at. Returns None if nothing.

    Writes to audit log: one `acknowledged` row (pending -> processing).
    """
    consumer = await session.get(Consumer, consumer_id)
    if consumer is None:
        raise NotFoundError(f"Consumer not found: {consumer_id}")
    # Only pull consumers (http/sdk) may poll. Webhook deliveries are owned by the
    # dispatcher; polling them would race it and double-deliver.
    if consumer.type not in (ConsumerType.http, ConsumerType.sdk):
        raise ConflictError(f"Consumer type '{consumer.type.value}' cannot poll (push consumer)")
    if not consumer.is_active:
        raise ConflictError("Consumer is inactive")
    queue = await session.get(Queue, consumer.queue_id)
    if queue.is_paused:
        return None  # paused queue: nothing to hand out

    order_clause = (
        "m.sequence_num ASC" if queue.fifo_enabled else "d.visible_after ASC, d.created_at ASC"
    )
    row = (
        await session.execute(
            text(
                f"""
                SELECT d.id
                FROM deliveries d
                JOIN messages m ON m.id = d.message_id
                WHERE d.consumer_id = :cid
                  AND d.status = 'pending'
                  AND d.visible_after <= now()
                ORDER BY {order_clause}
                LIMIT 1
                FOR UPDATE OF d SKIP LOCKED
                """
            ),
            {"cid": str(consumer_id)},
        )
    ).first()
    if row is None:
        return None

    delivery = await get_delivery(session, row[0])
    message = await session.get(Message, delivery.message_id)

    audit_service.log_transition(
        session,
        delivery,
        event_type=audit_service.EVENT_ACKNOWLEDGED,
        to_status=DeliveryStatus.processing,
        context={"via": "poll"},
    )
    delivery.status = DeliveryStatus.processing
    delivery.visible_after = _now() + timedelta(seconds=queue.visibility_timeout_seconds)
    await session.flush()

    return {
        "delivery": delivery,
        "payload": message.payload,
        "sequence_num": message.sequence_num,
    }


# --------------------------------------------------------------------------- #
# Explicit transitions
# --------------------------------------------------------------------------- #
async def ack(session: AsyncSession, delivery_id: uuid.UUID) -> Delivery:
    """Move a pending delivery to processing and start its visibility timeout.

    Writes to audit log: one `acknowledged` row (pending -> processing).
    """
    delivery = await get_delivery(session, delivery_id)
    if delivery.status not in (DeliveryStatus.pending, DeliveryStatus.processing):
        raise ConflictError(f"Cannot ack delivery in status {delivery.status.value}")
    queue = await _queue_for_delivery(session, delivery)

    audit_service.log_transition(
        session,
        delivery,
        event_type=audit_service.EVENT_ACKNOWLEDGED,
        to_status=DeliveryStatus.processing,
    )
    delivery.status = DeliveryStatus.processing
    delivery.visible_after = _now() + timedelta(seconds=queue.visibility_timeout_seconds)
    await session.flush()
    return delivery


async def complete(
    session: AsyncSession, delivery_id: uuid.UUID, remark: str | None, meta: dict | None
) -> Delivery:
    """Mark a delivery completed (consumer acknowledged success).

    Writes to audit log: one `status_updated` row (-> completed).
    """
    delivery = await get_delivery(session, delivery_id)
    if delivery.status in (DeliveryStatus.completed,):
        raise ConflictError("Delivery already completed")

    audit_service.log_transition(
        session,
        delivery,
        event_type=audit_service.EVENT_STATUS_UPDATED,
        to_status=DeliveryStatus.completed,
        remark=remark,
        meta=meta or {},
    )
    delivery.status = DeliveryStatus.completed
    delivery.completed_at = _now()
    if remark:
        delivery.last_remark = remark
    if meta:
        delivery.meta = {**delivery.meta, **meta}
    await session.flush()
    return delivery


def apply_failure(
    session: AsyncSession,
    delivery: Delivery,
    queue: Queue,
    *,
    remark: str | None,
    meta: dict | None = None,
    context: dict | None = None,
) -> Delivery:
    """Shared retry-or-fail logic. Increments attempt_count, then either schedules
    a retry (status pending, delayed) or marks failed when retries are exhausted.

    Semantics: `queue.max_retries` is the max TOTAL delivery attempts. attempt_count
    starts at 0; each failure increments it; when it reaches max_retries the delivery
    is terminal. (e.g. max_retries=3 => up to 3 attempts.)

    Writes to audit log: one `retry_scheduled` row (on retry) or one
    `status_updated` row (-> failed). Synchronous (no flush) so callers control txn.
    """
    delivery.attempt_count += 1
    if delivery.last_remark is not None or remark:
        delivery.last_remark = remark
    if meta:
        delivery.meta = {**delivery.meta, **meta}

    if delivery.attempt_count < queue.max_retries:
        audit_service.log_transition(
            session,
            delivery,
            event_type=audit_service.EVENT_RETRY_SCHEDULED,
            to_status=DeliveryStatus.pending,
            remark=remark,
            context={**(context or {}), "attempt_count": delivery.attempt_count},
        )
        delivery.status = DeliveryStatus.pending
        delivery.visible_after = _now() + timedelta(seconds=queue.retry_delay_seconds)
    else:
        # Retries exhausted. Route to DLQ ('dead') when enabled, else terminal 'failed'.
        terminal = DeliveryStatus.dead if queue.dlq_enabled else DeliveryStatus.failed
        event = (
            audit_service.EVENT_DEAD_LETTERED
            if terminal == DeliveryStatus.dead
            else audit_service.EVENT_STATUS_UPDATED
        )
        audit_service.log_transition(
            session,
            delivery,
            event_type=event,
            to_status=terminal,
            remark=remark,
            context={**(context or {}), "attempt_count": delivery.attempt_count},
        )
        delivery.status = terminal
    return delivery


async def fail(
    session: AsyncSession, delivery_id: uuid.UUID, remark: str, meta: dict | None
) -> Delivery:
    """Mark a delivery failed (consumer reported failure); schedules retry if allowed.

    Writes to audit log: `retry_scheduled` or `status_updated` (-> failed).
    """
    delivery = await get_delivery(session, delivery_id)
    if delivery.status == DeliveryStatus.completed:
        raise ConflictError("Cannot fail a completed delivery")
    queue = await _queue_for_delivery(session, delivery)
    apply_failure(session, delivery, queue, remark=remark, meta=meta)
    await session.flush()
    return delivery


async def add_remark(session: AsyncSession, delivery_id: uuid.UUID, remark: str) -> Delivery:
    """Attach a free-text remark to a delivery without changing its status.

    Writes to audit log: one `remark_added` row.
    """
    delivery = await get_delivery(session, delivery_id)
    audit_service.write_log(
        session,
        delivery_id=delivery.id,
        event_type=audit_service.EVENT_REMARK_ADDED,
        from_status=delivery.status,
        to_status=delivery.status,
        remark=remark,
    )
    delivery.last_remark = remark
    await session.flush()
    return delivery


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #
async def delivery_history(session: AsyncSession, delivery_id: uuid.UUID):
    """Return the full append-only delivery_logs trail for a delivery."""
    from app.models.delivery_log import DeliveryLog

    await get_delivery(session, delivery_id)
    rows = (
        await session.execute(
            select(DeliveryLog)
            .where(DeliveryLog.delivery_id == delivery_id)
            .order_by(DeliveryLog.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def list_dlq(
    session: AsyncSession, queue_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[Delivery], int]:
    """List dead-lettered deliveries for a queue (status='dead')."""
    base = (
        select(Delivery)
        .join(Message, Message.id == Delivery.message_id)
        .where(Message.queue_id == queue_id, Delivery.status == DeliveryStatus.dead)
    )
    total = (
        await session.execute(
            select(func.count())
            .select_from(Delivery)
            .join(Message, Message.id == Delivery.message_id)
            .where(Message.queue_id == queue_id, Delivery.status == DeliveryStatus.dead)
        )
    ).scalar_one()
    rows = (
        await session.execute(
            base.order_by(Delivery.updated_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


def requeue(session: AsyncSession, delivery: Delivery) -> Delivery:
    """Reset a delivery back to pending (attempt_count=0) for redelivery.

    Writes to audit log: one `requeued` row. Synchronous (caller commits).
    """
    audit_service.log_transition(
        session,
        delivery,
        event_type=audit_service.EVENT_REQUEUED,
        to_status=DeliveryStatus.pending,
    )
    delivery.status = DeliveryStatus.pending
    delivery.attempt_count = 0
    delivery.visible_after = _now()
    delivery.completed_at = None
    return delivery


def discard(session: AsyncSession, delivery: Delivery) -> Delivery:
    """Dismiss a dead delivery (mark failed, removed from the DLQ view).

    Writes to audit log: one `discarded` row.
    """
    audit_service.log_transition(
        session,
        delivery,
        event_type=audit_service.EVENT_DISCARDED,
        to_status=DeliveryStatus.failed,
        remark="discarded from DLQ",
    )
    delivery.status = DeliveryStatus.failed
    return delivery


async def list_consumer_deliveries(
    session: AsyncSession,
    consumer_id: uuid.UUID,
    status: DeliveryStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[Delivery], int]:
    """List deliveries for a consumer, optionally filtered by status."""
    filters = [Delivery.consumer_id == consumer_id]
    if status is not None:
        filters.append(Delivery.status == status)
    total = (
        await session.execute(select(func.count()).select_from(Delivery).where(*filters))
    ).scalar_one()
    rows = (
        await session.execute(
            select(Delivery)
            .where(*filters)
            .order_by(Delivery.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total
