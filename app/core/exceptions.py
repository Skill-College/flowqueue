"""Custom exception classes and FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class FlowQueueError(Exception):
    """Base error. status_code maps to the HTTP response code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "error"

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class NotFoundError(FlowQueueError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(FlowQueueError):
    """409 — e.g. duplicate name / idempotency / invalid state transition."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(FlowQueueError):
    status_code = 422  # Unprocessable Content
    code = "validation_error"


class SSRFError(ValidationError):
    """Raised when a webhook/workflow endpoint URL targets a forbidden host."""

    code = "ssrf_blocked"


class AuthError(FlowQueueError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


def _handler(request: Request, exc: FlowQueueError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "context": exc.context}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers for all FlowQueueError subclasses."""

    @app.exception_handler(FlowQueueError)
    async def _flowqueue_error_handler(request: Request, exc: FlowQueueError) -> JSONResponse:
        return _handler(request, exc)
