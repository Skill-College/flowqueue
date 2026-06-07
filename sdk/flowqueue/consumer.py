"""High-level pull consumer with an optional run() loop."""

from __future__ import annotations

import time
from typing import Callable, Optional

from .client import FlowQueueClient
from .models import Delivery


class FlowQueueConsumer:
    """Pull consumer bound to a single consumer id.

    Example:
        from flowqueue import FlowQueueClient, FlowQueueConsumer
        client = FlowQueueClient(url, key)
        consumer = FlowQueueConsumer(client, consumer_id)

        # one-shot
        d = consumer.poll()
        if d:
            consumer.complete(d.id, remark="ok")

        # or run forever (handler return => complete, raise => fail)
        consumer.run(lambda d: process(d.payload))
    """

    def __init__(self, client: FlowQueueClient, consumer_id: str) -> None:
        self.client = client
        self.consumer_id = consumer_id

    def poll(self) -> Optional[Delivery]:
        data = self.client.poll(self.consumer_id)
        return Delivery.from_dict(data) if data else None

    def ack(self, delivery_id: str) -> dict:
        return self.client.ack(delivery_id)

    def complete(self, delivery_id: str, remark: str | None = None) -> dict:
        return self.client.complete(delivery_id, remark=remark)

    def fail(self, delivery_id: str, remark: str, metadata: dict | None = None) -> dict:
        return self.client.fail(delivery_id, remark, metadata)

    def add_remark(self, delivery_id: str, remark: str) -> dict:
        return self.client.add_remark(delivery_id, remark)

    def run(
        self,
        handler: Callable[[Delivery], None],
        *,
        poll_interval: float = 2.0,
        auto_complete: bool = True,
        max_iterations: int | None = None,
    ) -> None:
        """Continuously poll and dispatch deliveries to `handler`.

        On success the delivery is completed (when auto_complete); on exception it is
        failed (triggering retry/DLQ per queue config). Sleeps poll_interval when idle.
        Set max_iterations to bound the loop (useful for tests/cron-style runs).
        """
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            iterations += 1
            delivery = self.poll()
            if delivery is None:
                time.sleep(poll_interval)
                continue
            try:
                handler(delivery)
                if auto_complete:
                    self.complete(delivery.id, remark="ok")
            except Exception as exc:  # noqa: BLE001
                self.fail(delivery.id, remark=str(exc)[:500])
