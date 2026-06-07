"""v1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    api_keys,
    auth,
    consumers,
    deliveries,
    events,
    feedback,
    messages,
    queues,
    replay,
    stats,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(events.router)
api_router.include_router(queues.router)
api_router.include_router(messages.router)
api_router.include_router(consumers.router)
api_router.include_router(deliveries.router)
api_router.include_router(replay.router)
api_router.include_router(stats.router)
api_router.include_router(api_keys.router)
api_router.include_router(feedback.router)
