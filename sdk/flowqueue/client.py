"""FlowQueue synchronous client — full coverage of the FlowQueue HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from .errors import ApiError


def _iso(value: Optional[datetime | str]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else value


class FlowQueueClient:
    """Authenticated client for a FlowQueue server.

    Example:
        from flowqueue import FlowQueueClient
        client = FlowQueueClient("https://flowqueue.example.com", "fq_...")
        q = client.create_queue("orders")
        client.publish(q["id"], {"hello": "world"}, idempotency_key="abc")
    """

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    # ---- lifecycle -------------------------------------------------------- #
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "FlowQueueClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- low-level -------------------------------------------------------- #
    def _request(self, method: str, path: str, **kw) -> Any:
        resp = self._http.request(method, path, **kw)
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

    _v = "/api/v1"

    # ---- queues ----------------------------------------------------------- #
    def create_queue(self, name: str, **opts) -> dict:
        """Create a queue. opts: fifo_enabled, max_retries, retry_delay_seconds,
        visibility_timeout_seconds, retention_seconds, success_retention_seconds,
        failed_retention_seconds, dlq_enabled, metadata."""
        return self._request("POST", f"{self._v}/queues", json={"name": name, **opts})

    def list_queues(self, archived: bool = False, limit: int = 100, offset: int = 0) -> dict:
        return self._request(
            "GET", f"{self._v}/queues",
            params={"archived": archived, "limit": limit, "offset": offset},
        )

    def get_queue(self, queue_id: str) -> dict:
        return self._request("GET", f"{self._v}/queues/{queue_id}")

    def update_queue(self, queue_id: str, **fields) -> dict:
        return self._request("PATCH", f"{self._v}/queues/{queue_id}", json=fields)

    def archive_queue(self, queue_id: str) -> dict:
        return self._request("DELETE", f"{self._v}/queues/{queue_id}")

    def restore_queue(self, queue_id: str) -> dict:
        return self._request("PATCH", f"{self._v}/queues/{queue_id}", json={"is_active": True})

    def pause_queue(self, queue_id: str) -> dict:
        return self._request("POST", f"{self._v}/queues/{queue_id}/pause")

    def resume_queue(self, queue_id: str) -> dict:
        return self._request("POST", f"{self._v}/queues/{queue_id}/resume")

    def queue_stats(self, queue_id: str) -> dict:
        return self._request("GET", f"{self._v}/queues/{queue_id}/stats")

    def queue_timeseries(self, queue_id: str, minutes: int = 60) -> list:
        return self._request(
            "GET", f"{self._v}/queues/{queue_id}/timeseries", params={"minutes": minutes}
        )

    def purge_queue(self, queue_id: str) -> dict:
        """Permanently delete all pending (un-started) messages. Cannot be undone.
        Returns {"deliveries": n, "messages": m}."""
        return self._request("POST", f"{self._v}/queues/{queue_id}/purge")

    def queue_timeline(
        self,
        queue_id: str,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Queue activity timeline (newest first). Optionally filter by action, e.g.
        'queue_purged', 'messages_expired'."""
        params: dict = {"limit": limit, "offset": offset}
        if action:
            params["action"] = action
        return self._request(
            "GET", f"{self._v}/queues/{queue_id}/timeline", params=params
        )

    # ---- consumers -------------------------------------------------------- #
    def create_consumer(
        self,
        queue_id: str,
        name: str,
        type: str = "http",
        *,
        endpoint_url: str | None = None,
        routing_rules: list | None = None,
        match_mode: str = "any",
        auto_complete: bool = True,
        signing_secret: str | None = None,
        custom_headers: dict | None = None,
        metadata: dict | None = None,
    ) -> dict:
        body = {
            "name": name,
            "type": type,
            "endpoint_url": endpoint_url,
            "routing_rules": routing_rules or [],
            "match_mode": match_mode,
            "auto_complete": auto_complete,
            "signing_secret": signing_secret,
            "custom_headers": custom_headers or {},
            "metadata": metadata or {},
        }
        return self._request("POST", f"{self._v}/queues/{queue_id}/consumers", json=body)

    def list_consumers(self, queue_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self._request(
            "GET", f"{self._v}/queues/{queue_id}/consumers",
            params={"limit": limit, "offset": offset},
        )

    def get_consumer(self, consumer_id: str) -> dict:
        return self._request("GET", f"{self._v}/consumers/{consumer_id}")

    def update_consumer(self, queue_id: str, consumer_id: str, **fields) -> dict:
        return self._request(
            "PATCH", f"{self._v}/queues/{queue_id}/consumers/{consumer_id}", json=fields
        )

    def deactivate_consumer(self, queue_id: str, consumer_id: str) -> dict:
        return self._request("DELETE", f"{self._v}/queues/{queue_id}/consumers/{consumer_id}")

    def test_consumer(self, queue_id: str, consumer_id: str) -> dict:
        return self._request("POST", f"{self._v}/queues/{queue_id}/consumers/{consumer_id}/test")

    # ---- messages (producer) --------------------------------------------- #
    def publish(
        self,
        queue_id: str,
        payload: dict,
        idempotency_key: str | None = None,
        *,
        delay_seconds: int | None = None,
        deliver_at: datetime | str | None = None,
    ) -> dict:
        """Publish a message. Optionally schedule it with delay_seconds or deliver_at."""
        body: dict[str, Any] = {"payload": payload}
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if delay_seconds is not None:
            body["delay_seconds"] = delay_seconds
        if deliver_at is not None:
            body["deliver_at"] = _iso(deliver_at)
        return self._request("POST", f"{self._v}/queues/{queue_id}/messages", json=body)

    def list_messages(self, queue_id: str, limit: int = 50, offset: int = 0) -> dict:
        return self._request(
            "GET", f"{self._v}/queues/{queue_id}/messages",
            params={"limit": limit, "offset": offset},
        )

    def get_message(self, queue_id: str, message_id: str) -> dict:
        return self._request("GET", f"{self._v}/queues/{queue_id}/messages/{message_id}")

    # ---- deliveries (consumer) ------------------------------------------- #
    def poll(self, consumer_id: str) -> dict | None:
        return self._request("POST", f"{self._v}/consumers/{consumer_id}/poll")

    def ack(self, delivery_id: str) -> dict:
        return self._request("POST", f"{self._v}/deliveries/{delivery_id}/ack")

    def complete(self, delivery_id: str, remark: str | None = None, metadata: dict | None = None) -> dict:
        return self._request(
            "POST", f"{self._v}/deliveries/{delivery_id}/complete",
            json={"remark": remark, "metadata": metadata or {}},
        )

    def fail(self, delivery_id: str, remark: str, metadata: dict | None = None) -> dict:
        return self._request(
            "POST", f"{self._v}/deliveries/{delivery_id}/fail",
            json={"remark": remark, "metadata": metadata or {}},
        )

    def add_remark(self, delivery_id: str, remark: str) -> dict:
        return self._request(
            "POST", f"{self._v}/deliveries/{delivery_id}/remark", json={"remark": remark}
        )

    def get_delivery(self, delivery_id: str) -> dict:
        return self._request("GET", f"{self._v}/deliveries/{delivery_id}")

    def delivery_history(self, delivery_id: str) -> list:
        return self._request("GET", f"{self._v}/deliveries/{delivery_id}/history")

    def list_consumer_deliveries(
        self, consumer_id: str, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._request(
            "GET", f"{self._v}/consumers/{consumer_id}/deliveries", params=params
        )

    # ---- replay ----------------------------------------------------------- #
    def replay_failed(self, consumer_id: str) -> dict:
        return self._request("POST", f"{self._v}/consumers/{consumer_id}/replay/failed")

    def replay_range(self, consumer_id: str, from_ts: datetime | str, to_ts: datetime | str) -> dict:
        return self._request(
            "POST", f"{self._v}/consumers/{consumer_id}/replay/range",
            json={"from_ts": _iso(from_ts), "to_ts": _iso(to_ts)},
        )

    def replay_selected(self, consumer_id: str, message_ids: list[str]) -> dict:
        return self._request(
            "POST", f"{self._v}/consumers/{consumer_id}/replay/selected",
            json={"message_ids": message_ids},
        )

    def replay_backfill(self, consumer_id: str) -> dict:
        return self._request("POST", f"{self._v}/consumers/{consumer_id}/replay/backfill")

    def get_replay(self, replay_id: str) -> dict:
        return self._request("GET", f"{self._v}/replay/{replay_id}")

    # ---- dead-letter queue ----------------------------------------------- #
    def dlq_list(self, queue_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self._request(
            "GET", f"{self._v}/queues/{queue_id}/dlq", params={"limit": limit, "offset": offset}
        )

    def requeue(self, delivery_id: str) -> dict:
        return self._request("POST", f"{self._v}/deliveries/{delivery_id}/requeue")

    def discard(self, delivery_id: str) -> dict:
        return self._request("POST", f"{self._v}/deliveries/{delivery_id}/discard")

    def requeue_all(self, queue_id: str) -> dict:
        return self._request("POST", f"{self._v}/queues/{queue_id}/dlq/requeue")

    # ---- api keys --------------------------------------------------------- #
    def create_api_key(self, name: str, scopes: list[str] | None = None) -> dict:
        return self._request(
            "POST", f"{self._v}/api-keys",
            json={"name": name, "scopes": scopes or ["publish", "consume"]},
        )
