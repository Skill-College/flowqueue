"""Resource ownership authorization helpers (multi-tenancy enforcement).

Isolation rule: a user may only access queues they own (and everything nested
under them — consumers, messages, deliveries, replays). Admins bypass the check.
Authorization failures raise NotFoundError (404) rather than 403 so existence of
another user's resources is not leaked.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.consumer import Consumer
from app.models.delivery import Delivery
from app.models.message import Message
from app.models.queue import Queue
from app.models.replay_request import ReplayRequest
from app.models.user import User


def _owns(queue: Queue, user: User) -> bool:
    return user.is_admin or (queue.owner_id is not None and queue.owner_id == user.id)


async def authorize_queue(session: AsyncSession, queue_id: uuid.UUID, user: User) -> Queue:
    """Return the queue if the user owns it (or is admin); else 404."""
    queue = await session.get(Queue, queue_id)
    if queue is None or not _owns(queue, user):
        raise NotFoundError(f"Queue not found: {queue_id}")
    return queue


async def authorize_consumer(
    session: AsyncSession, consumer_id: uuid.UUID, user: User
) -> Consumer:
    """Return the consumer if the user owns its queue (or is admin); else 404."""
    consumer = await session.get(Consumer, consumer_id)
    if consumer is None:
        raise NotFoundError(f"Consumer not found: {consumer_id}")
    await authorize_queue(session, consumer.queue_id, user)
    return consumer


async def authorize_delivery(
    session: AsyncSession, delivery_id: uuid.UUID, user: User
) -> Delivery:
    """Return the delivery if the user owns its queue (via message → queue); else 404."""
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None:
        raise NotFoundError(f"Delivery not found: {delivery_id}")
    queue_id = (
        await session.execute(
            select(Message.queue_id).where(Message.id == delivery.message_id)
        )
    ).scalar_one()
    await authorize_queue(session, queue_id, user)
    return delivery


async def authorize_replay(
    session: AsyncSession, replay_id: uuid.UUID, user: User
) -> ReplayRequest:
    """Return the replay request if the user owns the target consumer's queue; else 404."""
    req = await session.get(ReplayRequest, replay_id)
    if req is None:
        raise NotFoundError(f"Replay request not found: {replay_id}")
    await authorize_consumer(session, req.consumer_id, user)
    return req
