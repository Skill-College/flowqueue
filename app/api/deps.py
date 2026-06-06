"""Shared API dependencies."""

from fastapi import Query


class Pagination:
    """Common limit/offset pagination query params."""

    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset
