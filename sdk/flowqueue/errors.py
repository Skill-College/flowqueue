"""SDK exceptions."""

from __future__ import annotations


class FlowQueueError(Exception):
    """Base error for the FlowQueue SDK."""


class ApiError(FlowQueueError):
    """Raised on a non-2xx API response.

    Attributes:
        status: HTTP status code.
        code: machine-readable error code from the API envelope (if any).
        message: human-readable message.
    """

    def __init__(self, status: int, code: str | None, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"[{status}] {code or 'error'}: {message}")
