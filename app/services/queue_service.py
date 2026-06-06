"""Queue service — CRUD, soft delete, and stats. Does not write delivery_logs."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.consumer import Consumer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.models.queue import Queue
from app.models.queue_sequence import QueueSequence
from app.schemas.queue import QueueCreate, QueueStats, QueueUpdate


async def create_queue(session: AsyncSession, data: QueueCreate) -> Queue:
    """Create a queue and its per-queue sequence counter row."""
    queue = Queue(
        name=data.name,
        fifo_enabled=data.fifo_enabled,
        max_retries=data.max_retries,
        retry_delay_seconds=data.retry_delay_seconds,
        retention_seconds=data.retention_seconds,
        processed_retention_seconds=data.processed_retention_seconds,
        visibility_timeout_seconds=data.visibility_timeout_seconds,
        meta=data.metadata,
    )
    session.add(queue)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(f"Queue name already exists: {data.name}") from exc
    session.add(QueueSequence(queue_id=queue.id, last_value=0))
    await session.flush()
    return queue


async def get_queue(session: AsyncSession, queue_id: uuid.UUID) -> Queue:
    queue = await session.get(Queue, queue_id)
    if queue is None:
        raise NotFoundError(f"Queue not found: {queue_id}")
    return queue


async def get_active_queue(session: AsyncSession, queue_id: uuid.UUID) -> Queue:
    """Fetch a queue and require it to be active (used on the publish path)."""
    queue = await get_queue(session, queue_id)
    if not queue.is_active:
        raise ConflictError(f"Queue is not active: {queue_id}")
    return queue


async def list_queues(session: AsyncSession, limit: int, offset: int) -> tuple[list[Queue], int]:
    total = (await session.execute(select(func.count()).select_from(Queue))).scalar_one()
    rows = (
        await session.execute(
            select(Queue).order_by(Queue.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def update_queue(session: AsyncSession, queue_id: uuid.UUID, data: QueueUpdate) -> Queue:
    queue = await get_queue(session, queue_id)
    payload = data.model_dump(exclude_unset=True)
    if "metadata" in payload:
        queue.meta = payload.pop("metadata")
    for field, value in payload.items():
        setattr(queue, field, value)
    await session.flush()
    return queue


async def soft_delete_queue(session: AsyncSession, queue_id: uuid.UUID) -> Queue:
    """Soft delete by setting is_active=False (rows are preserved)."""
    queue = await get_queue(session, queue_id)
    queue.is_active = False
    await session.flush()
    return queue


async def queue_stats(session: AsyncSession, queue_id: uuid.UUID) -> QueueStats:
    """Compute queue depth, per-status delivery counts, and max consumer lag."""
    await get_queue(session, queue_id)

    status_rows = (
        await session.execute(
            select(Delivery.status, func.count())
            .join(Message, Delivery.message_id == Message.id)
            .where(Message.queue_id == queue_id)
            .group_by(Delivery.status)
        )
    ).all()
    counts = {status.value: 0 for status in DeliveryStatus}
    for status, count in status_rows:
        counts[status.value] = count

    total_messages = (
        await session.execute(
            select(func.count()).select_from(Message).where(Message.queue_id == queue_id)
        )
    ).scalar_one()

    consumer_count = (
        await session.execute(
            select(func.count()).select_from(Consumer).where(Consumer.queue_id == queue_id)
        )
    ).scalar_one()

    oldest_pending = (
        await session.execute(
            select(func.min(Delivery.created_at))
            .join(Message, Delivery.message_id == Message.id)
            .where(
                Message.queue_id == queue_id,
                Delivery.status == DeliveryStatus.pending,
            )
        )
    ).scalar_one()

    lag = None
    if oldest_pending is not None:
        now = (await session.execute(select(func.now()))).scalar_one()
        lag = (now - oldest_pending).total_seconds()

    return QueueStats(
        queue_id=queue_id,
        pending=counts["pending"],
        processing=counts["processing"],
        completed=counts["completed"],
        failed=counts["failed"],
        total_messages=total_messages,
        consumer_count=consumer_count,
        max_consumer_lag_seconds=lag,
    )
