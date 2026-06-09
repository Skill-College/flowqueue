"""FlowQueue async runtime client.

Scope is intentionally narrow: **produce** messages and **consume** deliveries.
Queue/consumer management, API keys, replay, and DLQ are handled in the FlowQueue UI
(or directly via the HTTP API), not here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from .errors import ApiError
from .types import DeliveryOut, MessageOut


def _iso(value: Optional[datetime | str]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else value


class AsyncFlowQueueClient:
    """Async authenticated client for a FlowQueue server.

    Example:
        import asyncio
        from flowqueue import AsyncFlowQueueClient

        async def main():
            async with AsyncFlowQueueClient("https://flowqueue.example.com", "fq_...") as c:
                await c.publish("<queue_id>", {"hello": "world"}, idempotency_key="abc")

        asyncio.run(main())
    """

    _v = "/api/v1"

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    # ---- lifecycle -------------------------------------------------------- #
    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncFlowQueueClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ---- low-level -------------------------------------------------------- #
    async def _request(self, method: str, path: str, **kw: Any) -> Any:
        resp = await self._http.request(method, path, **kw)
        if resp.status_code == 204 or not resp.content:
            if 200 <= resp.status_code < 300:
                return None
        try:
            body = resp.json()
        except ValueError:
            body = None
        if not (200 <= resp.status_code < 300):
            code, message = None, resp.text
            if isinstance(body, dict):
                err = body.get("error")
                if isinstance(err, dict):
                    code, message = err.get("code"), err.get("message", message)
                elif "detail" in body:
                    message = body["detail"]
            raise ApiError(resp.status_code, code, message or "request failed")
        return body

    # ---- producer --------------------------------------------------------- #
    async def publish(
        self,
        queue_id: str,
        payload: dict,
        idempotency_key: Optional[str] = None,
        *,
        delay_seconds: Optional[int] = None,
        deliver_at: Optional[datetime | str] = None,
    ) -> MessageOut:
        """Publish a message. Optionally schedule with delay_seconds or deliver_at."""
        body: dict[str, Any] = {"payload": payload}
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if delay_seconds is not None:
            body["delay_seconds"] = delay_seconds
        if deliver_at is not None:
            body["deliver_at"] = _iso(deliver_at)
        return await self._request("POST", f"{self._v}/queues/{queue_id}/messages", json=body)

    # ---- consumer lifecycle ---------------------------------------------- #
    async def poll(self, consumer_id: str) -> Optional[DeliveryOut]:
        """Claim the next delivery for a consumer, or None if the queue is empty."""
        return await self._request("POST", f"{self._v}/consumers/{consumer_id}/poll")

    async def ack(self, delivery_id: str) -> DeliveryOut:
        return await self._request("POST", f"{self._v}/deliveries/{delivery_id}/ack")

    async def complete(
        self,
        delivery_id: str,
        remark: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DeliveryOut:
        return await self._request(
            "POST",
            f"{self._v}/deliveries/{delivery_id}/complete",
            json={"remark": remark, "metadata": metadata or {}},
        )

    async def fail(
        self,
        delivery_id: str,
        remark: str,
        metadata: Optional[dict] = None,
    ) -> DeliveryOut:
        return await self._request(
            "POST",
            f"{self._v}/deliveries/{delivery_id}/fail",
            json={"remark": remark, "metadata": metadata or {}},
        )

    async def add_remark(self, delivery_id: str, remark: str) -> DeliveryOut:
        return await self._request(
            "POST", f"{self._v}/deliveries/{delivery_id}/remark", json={"remark": remark}
        )
