"""Worker runner — schedules all background jobs with APScheduler (AsyncIOScheduler).

Run as: python -m app.workers.runner  (the `worker` container's CMD). The API
process does NOT run this; the scheduler lives only here to avoid duplicate jobs
across gunicorn workers.
"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import configure_logging, get_logger
from app.workers import (
    replay_worker,
    retention_janitor,
    visibility_reclaim,
    webhook_dispatcher,
)

configure_logging()
log = get_logger("flowqueue.worker")


def _job(name: str, coro_fn):
    """Wrap a worker run_once coroutine with logging + error isolation."""

    async def _runner():
        try:
            handled = await coro_fn()
            if handled:
                log.info("worker.tick", job=name, handled=handled)
        except Exception:
            log.exception("worker.error", job=name)

    return _runner


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _job("visibility_reclaim", visibility_reclaim.run_once),
        "interval",
        seconds=10,
        id="visibility_reclaim",
        max_instances=1,
    )
    scheduler.add_job(
        _job("webhook_dispatcher", webhook_dispatcher.run_once),
        "interval",
        seconds=5,
        id="webhook_dispatcher",
        max_instances=1,
    )
    scheduler.add_job(
        _job("replay_worker", replay_worker.run_once),
        "interval",
        seconds=2,
        id="replay_worker",
        max_instances=1,
    )
    scheduler.add_job(
        _job("retention_janitor", retention_janitor.run_once),
        "interval",
        hours=1,
        id="retention_janitor",
        max_instances=1,
    )
    return scheduler


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    log.info("flowqueue.worker.start")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("flowqueue.worker.stop")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
