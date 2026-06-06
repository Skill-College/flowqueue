"""delivery_worker — placeholder for pull-based consumers.

HTTP and SDK consumers are PULL-based: they obtain work via the
POST /api/v1/consumers/{id}/poll endpoint (see delivery_service.poll_next), which
atomically claims the next pending delivery. They therefore need no background
push worker. Push delivery for webhook/workflow consumers lives in
webhook_dispatcher.py. This module is intentionally a no-op and registers no jobs.
"""


async def run_once() -> int:  # pragma: no cover - intentional no-op
    return 0
