"""retention_janitor worker — purges expired messages (and their deliveries).

Runs hourly. Deletes messages whose expires_at < now() AND whose deliveries are
ALL terminal (completed/failed). Deleting a message cascades to its deliveries;
delivery_logs are PRESERVED (delivery_id is set NULL by the FK) — logs are
append-only and never deleted by us.
"""

from sqlalchemy import text

from app.database import async_session_factory


async def run_once() -> int:
    """Delete one sweep of fully-terminal expired messages. Returns rows deleted."""
    async with async_session_factory() as session:
        # A message is purgeable when expired and it has no non-terminal deliveries.
        result = await session.execute(
            text(
                """
                DELETE FROM messages m
                WHERE m.expires_at < now()
                  AND NOT EXISTS (
                      SELECT 1 FROM deliveries d
                      WHERE d.message_id = m.id
                        AND d.status NOT IN ('completed', 'failed')
                  )
                """
            )
        )
        await session.commit()
        return result.rowcount or 0
