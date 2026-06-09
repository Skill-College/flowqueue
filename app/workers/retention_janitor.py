"""retention_janitor worker — permanently deletes expired messages by outcome.

Runs hourly. A message is purged when it is expired under the window for its
*outcome*, then its deliveries cascade away (delivery_logs are PRESERVED — the FK
sets delivery_id NULL; logs are append-only and never deleted by us).

Outcome windows (per queue):
  * all deliveries completed              -> success_retention_seconds (default 24h)
  * any delivery failed/dead (rest term.) -> failed_retention_seconds  (default 7d)
  * no deliveries (purged / never had any) -> fall back to expires_at (retention_seconds)

Reference time for terminal messages is the newest delivery terminal timestamp
(COALESCE completed_at, updated_at, message.published_at).

Per sweep it writes one `messages_expired` queue_log row per affected queue (counts
in context) — surfacing the metric in the Timeline tab and /metrics.
"""

from sqlalchemy import text

from app.database import async_session_factory
from app.models.queue import Queue
from app.services import queue_audit_service


def _retention_for(any_failed: bool, queue: Queue) -> int:
    """Pick the retention window (seconds) for a terminal message's outcome."""
    return queue.failed_retention_seconds if any_failed else queue.success_retention_seconds


async def run_once() -> int:
    """Delete one sweep of expired messages (outcome-aware). Returns rows deleted."""
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                """
                WITH agg AS (
                    SELECT m.id, m.queue_id,
                           bool_or(d.status IN ('failed','dead'))              AS any_failed,
                           bool_and(d.status IN ('completed','failed','dead')) AS all_terminal,
                           count(d.id)                                         AS n,
                           max(COALESCE(d.completed_at, d.updated_at, m.published_at)) AS terminal_at
                    FROM messages m
                    LEFT JOIN deliveries d ON d.message_id = m.id
                    GROUP BY m.id, m.queue_id
                )
                DELETE FROM messages m
                USING agg, queues q
                WHERE m.id = agg.id AND q.id = m.queue_id
                  AND (
                    (agg.n > 0 AND agg.all_terminal
                      AND now() - agg.terminal_at >
                          (CASE WHEN agg.any_failed THEN q.failed_retention_seconds
                                ELSE q.success_retention_seconds END) * interval '1 second')
                    OR (agg.n = 0 AND m.expires_at < now())
                  )
                RETURNING m.queue_id AS queue_id, agg.any_failed AS any_failed
                """
            )
        )
        rows = result.all()

        # Tally deletions per queue + outcome (NULL any_failed => no-delivery purge,
        # counted as success since there was no failure).
        tally: dict = {}
        for queue_id, any_failed in rows:
            bucket = tally.setdefault(queue_id, {"success": 0, "failed": 0})
            if any_failed:
                bucket["failed"] += 1
            else:
                bucket["success"] += 1

        for queue_id, counts in tally.items():
            s, f = counts["success"], counts["failed"]
            queue_audit_service.write_queue_log(
                session,
                queue_id=queue_id,
                action=queue_audit_service.MESSAGES_EXPIRED,
                remark=f"Expired {s + f} messages ({s} success, {f} failed)",
                context={"success": s, "failed": f, "total": s + f},
            )

        await session.commit()
        return len(rows)
