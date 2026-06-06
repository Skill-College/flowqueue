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
from app.models.consumer import Consumer
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
    queue = await session.get(Queue, consumer.queue_id)

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
        audit_service.log_transition(
            session,
            delivery,
            event_type=audit_service.EVENT_STATUS_UPDATED,
            to_status=DeliveryStatus.failed,
            remark=remark,
            context={**(context or {}), "attempt_count": delivery.attempt_count},
        )
        delivery.status = DeliveryStatus.failed
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
