"""visibility_reclaim worker — reclaims stuck `processing` deliveries.

Runs every 10s. Finds deliveries whose visibility timeout has lapsed and either
reschedules them (pending, attempt++) or fails them when retries are exhausted.
Uses SELECT FOR UPDATE SKIP LOCKED to avoid races with other workers/pollers.
Every reclaim writes a delivery_log in the same transaction.
"""

from sqlalchemy import select, text

from app.database import async_session_factory
from app.models.delivery import Delivery
from app.models.message import Message
from app.models.queue import Queue
from app.services import delivery_service

BATCH = 100


async def run_once() -> int:
    """Reclaim one batch of expired processing deliveries. Returns count handled."""
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id FROM deliveries
                    WHERE status = 'processing' AND visible_after < now()
                    ORDER BY visible_after ASC
                    LIMIT :batch
                    FOR UPDATE SKIP LOCKED
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

        # Map each delivery to its queue (for max_retries / retry_delay).
        queue_by_delivery: dict = {}
        for d in deliveries:
            queue = (
                await session.execute(
                    select(Queue)
                    .join(Message, Message.queue_id == Queue.id)
                    .where(Message.id == d.message_id)
                )
            ).scalar_one()
            queue_by_delivery[d.id] = queue

        for d in deliveries:
            delivery_service.apply_failure(
                session,
                d,
                queue_by_delivery[d.id],
                remark="visibility timeout expired",
                context={"reason": "visibility_reclaim"},
            )

        await session.commit()
        return len(deliveries)
