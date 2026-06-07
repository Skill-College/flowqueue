"""webhook_dispatcher worker — pushes pending deliveries to webhook consumers.

Runs every 5s. Claims a batch of pending push deliveries (FOR UPDATE SKIP LOCKED),
resolves each target via the routing engine, POSTs the payload, then records the
outcome — each transition writes a log.

On HTTP 2xx the outcome depends on the consumer's `auto_complete`:
  * True  -> mark the delivery `completed` (fire-and-forget).
  * False -> leave it `processing` and arm the visibility timeout; the receiver must
             call back complete/fail, else visibility_reclaim redelivers (then fails).
On non-2xx -> apply_failure (retry/fail).
"""

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, text

from app.database import async_session_factory
from app.models.consumer import Consumer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.message import Message
from app.models.queue import Queue
from app.services import audit_service, delivery_service, webhook_service

BATCH = 50


async def run_once() -> int:
    """Dispatch one batch of webhook deliveries. Returns count attempted."""
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT d.id
                    FROM deliveries d
                    JOIN consumers c ON c.id = d.consumer_id
                    JOIN queues q ON q.id = c.queue_id
                    WHERE d.status = 'pending'
                      AND d.visible_after <= now()
                      AND c.is_active = true
                      AND c.type = 'webhook'
                      AND q.is_active = true
                      AND q.is_paused = false
                    ORDER BY d.visible_after ASC
                    LIMIT :batch
                    FOR UPDATE OF d SKIP LOCKED
                    """
                ),
                {"batch": BATCH},
            )
        ).scalars().all()

        if not rows:
            return 0

        deliveries = (
            await session.execute(select(Delivery).where(Delivery.id.in_(rows)))
        ).scalars().all()

        # Cache the queue per delivery (for visibility timeout + retry config).
        queue_by_delivery: dict = {}
        for d in deliveries:
            consumer = await session.get(Consumer, d.consumer_id)
            queue_by_delivery[d.id] = await session.get(Queue, consumer.queue_id)

        # Mark claimed rows processing AND arm the visibility timeout so the
        # in-flight dispatch isn't reclaimed by visibility_reclaim mid-POST.
        now = datetime.now(timezone.utc)
        for d in deliveries:
            audit_service.log_transition(
                session,
                d,
                event_type=audit_service.EVENT_ACKNOWLEDGED,
                to_status=DeliveryStatus.processing,
                context={"via": "webhook_dispatcher"},
            )
            d.status = DeliveryStatus.processing
            d.visible_after = now + timedelta(
                seconds=queue_by_delivery[d.id].visibility_timeout_seconds
            )
        await session.commit()

        async with httpx.AsyncClient() as client:
            for d in deliveries:
                consumer = await session.get(Consumer, d.consumer_id)
                message = await session.get(Message, d.message_id)
                queue = queue_by_delivery[d.id]

                # Filter rules: if the payload doesn't pass, skip the POST and mark
                # the delivery completed (filtered out — a normal outcome).
                if not webhook_service.should_deliver(consumer, message.payload):
                    audit_service.log_transition(
                        session,
                        d,
                        event_type=audit_service.EVENT_STATUS_UPDATED,
                        to_status=DeliveryStatus.completed,
                        remark="filtered: no rule matched",
                        context={"filtered": True, "match_mode": consumer.match_mode},
                    )
                    d.status = DeliveryStatus.completed
                    d.completed_at = datetime.now(timezone.utc)
                    await session.commit()
                    continue

                result = await webhook_service.deliver(client, consumer, d, message)
                ctx = {
                    "target_url": result.target_url,
                    "status_code": result.status_code,
                    "detail": result.detail,
                }
                if result.success and consumer.auto_complete:
                    # Fire-and-forget: 2xx => completed.
                    audit_service.log_transition(
                        session,
                        d,
                        event_type=audit_service.EVENT_STATUS_UPDATED,
                        to_status=DeliveryStatus.completed,
                        context=ctx,
                    )
                    d.status = DeliveryStatus.completed
                    d.completed_at = datetime.now(timezone.utc)
                elif result.success:
                    # Delivered, awaiting an explicit callback. Keep it 'processing'
                    # and arm the visibility timeout so a no-ack redelivers it.
                    d.visible_after = datetime.now(timezone.utc) + timedelta(
                        seconds=queue.visibility_timeout_seconds
                    )
                    audit_service.log_transition(
                        session,
                        d,
                        event_type=audit_service.EVENT_STATUS_UPDATED,
                        to_status=DeliveryStatus.processing,
                        context={**ctx, "delivered": True, "awaiting_ack": True},
                    )
                    # status already 'processing' from the claim step.
                else:
                    delivery_service.apply_failure(
                        session, d, queue, remark=result.detail, context=ctx
                    )
                await session.commit()

        return len(deliveries)
