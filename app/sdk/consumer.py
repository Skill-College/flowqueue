"""FlowQueue SDK consumer — poll/ack/complete/fail/remark helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.sdk.client import FlowQueueClient


@dataclass
class Delivery:
    """A delivery handed to a consumer by poll()."""

    id: str
    message_id: str
    consumer_id: str
    status: str
    attempt_count: int
    payload: dict
    sequence_num: int
    raw: dict[str, Any]


class FlowQueueConsumer:
    """High-level pull consumer.

    Example:
        client = FlowQueueClient(url, key)
        consumer = FlowQueueConsumer(client, consumer_id)
        d = consumer.poll()
        if d:
            try:
                handle(d.payload)
                consumer.complete(d.id, remark="ok")
            except Exception as e:
                consumer.fail(d.id, remark=str(e))
    """

    def __init__(self, client: FlowQueueClient, consumer_id: str) -> None:
        self.client = client
        self.consumer_id = consumer_id

    def poll(self) -> Optional[Delivery]:
        """Claim the next pending delivery. Returns None if the queue is empty."""
        resp = self.client._post(f"/api/v1/consumers/{self.consumer_id}/poll")
        if resp.status_code == 204 or not resp.content:
            return None
        data = resp.json()
        if data is None:
            return None
        return Delivery(
            id=data["id"],
            message_id=data["message_id"],
            consumer_id=data["consumer_id"],
            status=data["status"],
            attempt_count=data["attempt_count"],
            payload=data["payload"],
            sequence_num=data["sequence_num"],
            raw=data,
        )

    def ack(self, delivery_id: str) -> dict:
        """Move a delivery to processing (start visibility timeout)."""
        return self.client._post(f"/api/v1/deliveries/{delivery_id}/ack").json()

    def complete(self, delivery_id: str, remark: str | None = None) -> dict:
        """Mark a delivery completed."""
        return self.client._post(
            f"/api/v1/deliveries/{delivery_id}/complete", json={"remark": remark}
        ).json()

    def fail(self, delivery_id: str, remark: str, metadata: dict | None = None) -> dict:
        """Mark a delivery failed (triggers retry if attempts remain)."""
        return self.client._post(
            f"/api/v1/deliveries/{delivery_id}/fail",
            json={"remark": remark, "metadata": metadata or {}},
        ).json()

    def add_remark(self, delivery_id: str, remark: str) -> dict:
        """Attach a remark to a delivery without changing its status."""
        return self.client._post(
            f"/api/v1/deliveries/{delivery_id}/remark", json={"remark": remark}
        ).json()
