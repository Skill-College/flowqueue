"""FlowQueue FastAPI application entrypoint (API only; workers run separately)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("flowqueue.api.start")
    yield
    log.info("flowqueue.api.stop")


app = FastAPI(
    title="FlowQueue",
    version="0.1.0",
    description="Cloud-native message processing platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Unauthenticated liveness probe."""
    return {"status": "ok"}


@app.get("/metrics", tags=["meta"])
async def metrics():
    """Prometheus-format global metrics (delivery counts by status)."""
    from fastapi.responses import PlainTextResponse
    from sqlalchemy import func, select

    from sqlalchemy import Integer, cast

    from app.database import async_session_factory
    from app.models.delivery import Delivery, DeliveryStatus
    from app.models.message import Message
    from app.models.queue import Queue
    from app.models.queue_log import QueueLog
    from app.services import queue_audit_service

    async with async_session_factory() as session:
        status_rows = (
            await session.execute(select(Delivery.status, func.count()).group_by(Delivery.status))
        ).all()
        counts = {s.value: 0 for s in DeliveryStatus}
        for status, n in status_rows:
            counts[status.value] = n
        queues_n = (await session.execute(select(func.count()).select_from(Queue))).scalar_one()
        messages_n = (await session.execute(select(func.count()).select_from(Message))).scalar_one()

        # Cumulative permanently-deleted messages by outcome, summed from the
        # append-only queue_logs `messages_expired` rows (survives restarts).
        purged = (
            await session.execute(
                select(
                    func.coalesce(
                        func.sum(cast(QueueLog.context["success"].astext, Integer)), 0
                    ),
                    func.coalesce(
                        func.sum(cast(QueueLog.context["failed"].astext, Integer)), 0
                    ),
                ).where(QueueLog.action == queue_audit_service.MESSAGES_EXPIRED)
            )
        ).one()
        purged_success, purged_failed = purged

    lines = [
        "# HELP flowqueue_deliveries Total deliveries by status",
        "# TYPE flowqueue_deliveries gauge",
    ]
    for status, n in counts.items():
        lines.append(f'flowqueue_deliveries{{status="{status}"}} {n}')
    lines.append("# HELP flowqueue_queues_total Total queues")
    lines.append("# TYPE flowqueue_queues_total gauge")
    lines.append(f"flowqueue_queues_total {queues_n}")
    lines.append("# HELP flowqueue_messages_total Total messages")
    lines.append("# TYPE flowqueue_messages_total gauge")
    lines.append(f"flowqueue_messages_total {messages_n}")
    lines.append("# HELP flowqueue_messages_purged_total Messages permanently deleted by retention")
    lines.append("# TYPE flowqueue_messages_purged_total counter")
    lines.append(f'flowqueue_messages_purged_total{{outcome="success"}} {purged_success}')
    lines.append(f'flowqueue_messages_purged_total{{outcome="failed"}} {purged_failed}')
    return PlainTextResponse("\n".join(lines) + "\n")
