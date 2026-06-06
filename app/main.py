"""FlowQueue FastAPI application entrypoint (API only; workers run separately)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
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

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Unauthenticated liveness probe."""
    return {"status": "ok"}
