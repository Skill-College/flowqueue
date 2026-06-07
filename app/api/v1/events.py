"""Realtime SSE event stream + per-queue time-series metrics.

SSE auth: EventSource can't send Authorization headers, so the stream accepts the
JWT access token as a query param (?access_token=). The handler polls delivery_logs
for the principal's owned queues and streams new events; the client uses them to
invalidate cached queries (near-realtime UI).
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import authorize_queue
from app.core.security import decode_token, get_principal
from app.database import async_session_factory, get_session
from app.models.user import User

router = APIRouter(tags=["events"])

Principal = Annotated[User, Depends(get_principal)]


@router.get("/events/stream")
async def event_stream(
    request: Request,
    access_token: str = Query(...),
):
    """Server-Sent Events: streams delivery-log events for the user's owned queues."""
    user_id = decode_token(access_token, expected_type="access")

    async def gen():
        cursor = datetime.now(timezone.utc)
        # Resolve admin flag + ownership once.
        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if user is None or not user.is_active:
                return
            is_admin = user.is_admin
        yield "retry: 3000\n\n"
        while True:
            if await request.is_disconnected():
                break
            async with async_session_factory() as session:
                rows = (
                    await session.execute(
                        text(
                            """
                            SELECT dl.event_type, dl.to_status, dl.created_at,
                                   m.queue_id, d.consumer_id
                            FROM delivery_logs dl
                            JOIN deliveries d ON d.id = dl.delivery_id
                            JOIN messages m ON m.id = d.message_id
                            JOIN queues q ON q.id = m.queue_id
                            WHERE dl.created_at > :cursor
                              AND (:is_admin OR q.owner_id = :uid)
                            ORDER BY dl.created_at ASC
                            LIMIT 100
                            """
                        ),
                        {"cursor": cursor, "is_admin": is_admin, "uid": str(user_id)},
                    )
                ).all()
            for event_type, to_status, created_at, queue_id, consumer_id in rows:
                cursor = max(cursor, created_at)
                payload = {
                    "event": event_type,
                    "to_status": to_status,
                    "queue_id": str(queue_id),
                    "consumer_id": str(consumer_id) if consumer_id else None,
                    "at": created_at.isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
            # heartbeat keeps the connection alive through proxies
            yield ": ping\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/queues/{queue_id}/timeseries")
async def queue_timeseries(
    queue_id: uuid.UUID,
    user: Principal,
    minutes: int = Query(default=60, ge=1, le=1440),
    session: AsyncSession = Depends(get_session),
):
    """Per-minute counts of created / completed / failed+dead events for a queue."""
    await authorize_queue(session, queue_id, user)
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (
        await session.execute(
            text(
                """
                SELECT date_trunc('minute', dl.created_at) AS bucket,
                       count(*) FILTER (WHERE dl.event_type = 'created')      AS created,
                       count(*) FILTER (WHERE dl.to_status = 'completed')     AS completed,
                       count(*) FILTER (WHERE dl.to_status IN ('failed','dead')) AS failed
                FROM delivery_logs dl
                JOIN deliveries d ON d.id = dl.delivery_id
                JOIN messages m ON m.id = d.message_id
                WHERE m.queue_id = :qid AND dl.created_at >= :since
                GROUP BY bucket
                ORDER BY bucket ASC
                """
            ),
            {"qid": str(queue_id), "since": since},
        )
    ).all()
    return [
        {
            "bucket": b.isoformat(),
            "created": int(c),
            "completed": int(comp),
            "failed": int(f),
        }
        for b, c, comp, f in rows
    ]
