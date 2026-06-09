"""Queue audit service — the single chokepoint for the queue_logs timeline.

Every queue-level lifecycle action (create/update/pause/resume/archive/restore/purge)
writes ONE queue_log row in the SAME transaction/session as the change, via
write_queue_log() below. queue_logs are APPEND-ONLY: this module only ever adds rows.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_log import QueueLog

# Canonical action types.
QUEUE_CREATED = "queue_created"
QUEUE_UPDATED = "queue_updated"
QUEUE_PAUSED = "queue_paused"
QUEUE_RESUMED = "queue_resumed"
QUEUE_ARCHIVED = "queue_archived"
QUEUE_RESTORED = "queue_restored"
QUEUE_PURGED = "queue_purged"
# Written by retention_janitor when expired messages are permanently deleted.
MESSAGES_EXPIRED = "messages_expired"

ACTIONS = (
    QUEUE_CREATED,
    QUEUE_UPDATED,
    QUEUE_PAUSED,
    QUEUE_RESUMED,
    QUEUE_ARCHIVED,
    QUEUE_RESTORED,
    QUEUE_PURGED,
    MESSAGES_EXPIRED,
)


def write_queue_log(
    session: AsyncSession,
    *,
    queue_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None = None,
    remark: str | None = None,
    meta: dict | None = None,
    context: dict | None = None,
) -> QueueLog:
    """Append one queue_log row to the session (NOT committed here).

    Caller commits as part of the surrounding transaction so the log and the
    state change land atomically. Returns the (pending) QueueLog instance.
    """
    log = QueueLog(
        queue_id=queue_id,
        action=action,
        actor_id=actor_id,
        remark=remark,
        meta=meta or {},
        context=context or {},
    )
    session.add(log)
    return log


async def list_queue_logs(
    session: AsyncSession,
    queue_id: uuid.UUID,
    limit: int,
    offset: int,
    action: str | None = None,
) -> tuple[list[QueueLog], int]:
    """List a queue's timeline (newest first), optionally filtered by action."""
    from sqlalchemy import func

    filters = [QueueLog.queue_id == queue_id]
    if action:
        filters.append(QueueLog.action == action)
    total = (
        await session.execute(select(func.count()).select_from(QueueLog).where(*filters))
    ).scalar_one()
    rows = (
        await session.execute(
            select(QueueLog)
            .where(*filters)
            .order_by(QueueLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total
