"""replay_worker — processes replay_requests by re-delivering existing messages.

Runs every 2s. Picks the oldest pending/running request, processes up to BATCH
messages per tick (which caps throughput at <=100 msg/s, the VPS rate limit),
and advances messages_replayed. Replay NEVER mutates messages: it creates new
deliveries, or resets existing ones to pending (logging the old state first).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.database import async_session_factory
from app.models.consumer import Consumer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.models.replay_request import ReplayRequest, ReplayStatus, ReplayType
from app.services import audit_service

BATCH = 100  # messages per tick; tick=2s => <=50 msg/s, within the 100 msg/s limit


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _target_message_ids(
    session, req: ReplayRequest, consumer: Consumer, limit: int, offset: int
) -> list[uuid.UUID]:
    """Resolve the next page of message ids to replay for this request type."""
    if req.replay_type == ReplayType.failed_only:
        # Deliveries currently failed for this consumer (reset clears them, so no offset).
        rows = (
            await session.execute(
                select(Delivery.message_id)
                .where(
                    Delivery.consumer_id == consumer.id,
                    Delivery.status == DeliveryStatus.failed,
                )
                .order_by(Delivery.message_id)
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    if req.replay_type == ReplayType.selected:
        ids = req.message_ids or []
        return list(ids[offset : offset + limit])

    stmt = select(Message.id).where(Message.queue_id == consumer.queue_id)
    if req.replay_type == ReplayType.date_range:
        if req.from_ts is not None:
            stmt = stmt.where(Message.published_at >= req.from_ts)
        if req.to_ts is not None:
            stmt = stmt.where(Message.published_at <= req.to_ts)
    # full_backfill: no extra filter
    rows = (
        await session.execute(
            stmt.order_by(Message.sequence_num).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows)


async def _replay_one(session, consumer: Consumer, message_id: uuid.UUID, replay_id: uuid.UUID) -> None:
    """Create or reset the delivery for (message, consumer) to pending + log it."""
    existing = (
        await session.execute(
            select(Delivery).where(
                Delivery.message_id == message_id,
                Delivery.consumer_id == consumer.id,
            )
        )
    ).scalar_one_or_none()

    context = {"replay_request_id": str(replay_id)}

    if existing is not None:
        context["previous_status"] = existing.status.value
        context["previous_attempt_count"] = existing.attempt_count
        audit_service.log_transition(
            session,
            existing,
            event_type=audit_service.EVENT_REPLAYED,
            to_status=DeliveryStatus.pending,
            context=context,
        )
        existing.status = DeliveryStatus.pending
        existing.attempt_count = 0
        existing.visible_after = _now()
        existing.completed_at = None
    else:
        delivery = Delivery(
            message_id=message_id,
            consumer_id=consumer.id,
            status=DeliveryStatus.pending,
            visible_after=_now(),
        )
        session.add(delivery)
        await session.flush()
        audit_service.write_log(
            session,
            delivery_id=delivery.id,
            event_type=audit_service.EVENT_REPLAYED,
            to_status=DeliveryStatus.pending,
            context={**context, "created": True},
        )


async def run_once() -> int:
    """Process one tick of the oldest active replay request. Returns messages replayed."""
    async with async_session_factory() as session:
        # Claim the oldest pending/running request with a row lock.
        row = (
            await session.execute(
                text(
                    """
                    SELECT id FROM replay_requests
                    WHERE status IN ('pending', 'running')
                    ORDER BY requested_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
            )
        ).first()
        if row is None:
            return 0

        req = await session.get(ReplayRequest, row[0])
        consumer = await session.get(Consumer, req.consumer_id)
        if consumer is None:
            req.status = ReplayStatus.failed
            req.error_message = "consumer no longer exists"
            req.completed_at = _now()
            await session.commit()
            return 0

        req.status = ReplayStatus.running
        offset = req.messages_replayed

        try:
            message_ids = await _target_message_ids(session, req, consumer, BATCH, offset)
            for mid in message_ids:
                await _replay_one(session, consumer, mid, req.id)
            req.messages_replayed += len(message_ids)

            # Fewer than a full batch => nothing more to do (terminal).
            if len(message_ids) < BATCH:
                req.status = ReplayStatus.completed
                req.completed_at = _now()
            await session.commit()
            return len(message_ids)
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            req = await session.get(ReplayRequest, row[0])
            req.status = ReplayStatus.failed
            req.error_message = str(exc)[:1000]
            req.completed_at = _now()
            await session.commit()
            return 0
