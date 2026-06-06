"""webhook_dispatcher worker — pushes pending deliveries to webhook/workflow consumers.

Runs every 5s. Claims a batch of pending push deliveries (FOR UPDATE SKIP LOCKED),
resolves each target via the routing engine, POSTs the payload, then records the
outcome (completed on 2xx, otherwise retry/fail) — each transition writes a log.
"""

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
    """Dispatch one batch of webhook/workflow deliveries. Returns count attempted."""
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT d.id
                    FROM deliveries d
                    JOIN consumers c ON c.id = d.consumer_id
                    WHERE d.status = 'pending'
                      AND d.visible_after <= now()
                      AND c.is_active = true
                      AND c.type IN ('webhook', 'workflow')
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

        # Mark all claimed rows processing first so a slow batch isn't re-claimed.
        for d in deliveries:
            audit_service.log_transition(
                session,
                d,
                event_type=audit_service.EVENT_ACKNOWLEDGED,
                to_status=DeliveryStatus.processing,
                context={"via": "webhook_dispatcher"},
            )
            d.status = DeliveryStatus.processing
        await session.commit()

        async with httpx.AsyncClient() as client:
            for d in deliveries:
                consumer = await session.get(Consumer, d.consumer_id)
                message = await session.get(Message, d.message_id)
                queue = await session.get(Queue, consumer.queue_id)

                result = await webhook_service.deliver(client, consumer, d, message)
                ctx = {
                    "target_url": result.target_url,
                    "status_code": result.status_code,
                    "detail": result.detail,
                }
                if result.success:
                    audit_service.log_transition(
                        session,
                        d,
                        event_type=audit_service.EVENT_STATUS_UPDATED,
                        to_status=DeliveryStatus.completed,
                        context=ctx,
                    )
                    d.status = DeliveryStatus.completed
                    from datetime import datetime, timezone

                    d.completed_at = datetime.now(timezone.utc)
                else:
                    delivery_service.apply_failure(
                        session, d, queue, remark=result.detail, context=ctx
                    )
                await session.commit()

        return len(deliveries)
