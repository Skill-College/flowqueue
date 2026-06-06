"""Replay service — creates replay_request jobs (processed by replay_worker).

Replay NEVER mutates messages. It re-delivers existing messages by creating new
deliveries (or resetting existing ones to pending). Job creation here is synchronous
and cheap; the heavy lifting runs in app/workers/replay_worker.py.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.replay_request import ReplayRequest, ReplayType
from app.services.consumer_service import get_consumer


async def _create(
    session: AsyncSession,
    consumer_id: uuid.UUID,
    replay_type: ReplayType,
    *,
    message_ids: list[uuid.UUID] | None = None,
    from_ts=None,
    to_ts=None,
) -> ReplayRequest:
    await get_consumer(session, consumer_id)
    req = ReplayRequest(
        consumer_id=consumer_id,
        replay_type=replay_type,
        message_ids=message_ids,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    session.add(req)
    await session.flush()
    return req


async def replay_failed(session: AsyncSession, consumer_id: uuid.UUID) -> ReplayRequest:
    """Queue a job to replay all of a consumer's failed deliveries."""
    return await _create(session, consumer_id, ReplayType.failed_only)


async def replay_range(
    session: AsyncSession, consumer_id: uuid.UUID, from_ts, to_ts
) -> ReplayRequest:
    """Queue a job to replay messages published within [from_ts, to_ts]."""
    return await _create(session, consumer_id, ReplayType.date_range, from_ts=from_ts, to_ts=to_ts)


async def replay_selected(
    session: AsyncSession, consumer_id: uuid.UUID, message_ids: list[uuid.UUID]
) -> ReplayRequest:
    """Queue a job to replay a specific set of message ids."""
    return await _create(session, consumer_id, ReplayType.selected, message_ids=message_ids)


async def replay_backfill(session: AsyncSession, consumer_id: uuid.UUID) -> ReplayRequest:
    """Queue a full backfill job (all messages on the consumer's queue)."""
    return await _create(session, consumer_id, ReplayType.full_backfill)


async def get_replay(session: AsyncSession, replay_id: uuid.UUID) -> ReplayRequest:
    from app.core.exceptions import NotFoundError

    req = await session.get(ReplayRequest, replay_id)
    if req is None:
        raise NotFoundError(f"Replay request not found: {replay_id}")
    return req
