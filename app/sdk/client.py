"""FlowQueue SDK client — thin synchronous wrapper over the HTTP API."""

from __future__ import annotations

from typing import Any

import httpx


class FlowQueueClient:
    """Authenticated client for the FlowQueue API.

    Example:
        client = FlowQueueClient("http://localhost:8000", "fq_...")
        client.publish(queue_id, {"hello": "world"}, idempotency_key="abc")
    """

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "FlowQueueClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def publish(
        self, queue_id: str, payload: dict, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """Publish a message to a queue. Returns the created (or existing) message."""
        body: dict[str, Any] = {"payload": payload}
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        resp = self._http.post(f"/api/v1/queues/{queue_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    # Low-level passthroughs used by FlowQueueConsumer.
    def _post(self, path: str, json: dict | None = None) -> httpx.Response:
        resp = self._http.post(path, json=json)
        resp.raise_for_status()
        return resp
