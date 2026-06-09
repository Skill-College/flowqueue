"""High-level async pull consumer with an optional run() loop."""

from __future__ import annotations

import asyncio
import inspect
from typing import Awaitable, Callable, Optional, Union

from .client import AsyncFlowQueueClient
from .types import DeliveryOut

Handler = Callable[[DeliveryOut], Union[None, Awaitable[None]]]


class AsyncFlowQueueConsumer:
    """Async pull consumer bound to a single consumer id.

    Example:
        import asyncio
        from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

        async def main():
            async with AsyncFlowQueueClient(url, key) as client:
                consumer = AsyncFlowQueueConsumer(client, "<consumer_id>")

                # one-shot
                d = await consumer.poll()
                if d:
                    await consumer.complete(d["id"], remark="ok")

                # or run forever (handler return => complete, raise => fail)
                await consumer.run(lambda d: process(d["payload"]))

        asyncio.run(main())
    """

    def __init__(self, client: AsyncFlowQueueClient, consumer_id: str) -> None:
        self.client = client
        self.consumer_id = consumer_id

    async def poll(self) -> Optional[DeliveryOut]:
        return await self.client.poll(self.consumer_id)

    async def ack(self, delivery_id: str) -> DeliveryOut:
        return await self.client.ack(delivery_id)

    async def complete(self, delivery_id: str, remark: Optional[str] = None) -> DeliveryOut:
        return await self.client.complete(delivery_id, remark=remark)

    async def fail(
        self, delivery_id: str, remark: str, metadata: Optional[dict] = None
    ) -> DeliveryOut:
        return await self.client.fail(delivery_id, remark, metadata)

    async def add_remark(self, delivery_id: str, remark: str) -> DeliveryOut:
        return await self.client.add_remark(delivery_id, remark)

    async def run(
        self,
        handler: Handler,
        *,
        poll_interval: float = 2.0,
        auto_complete: bool = True,
        max_iterations: Optional[int] = None,
    ) -> None:
        """Continuously poll and dispatch deliveries to `handler` (sync or async).

        On success the delivery is completed (when auto_complete); on exception it is
        failed (triggering retry/DLQ per queue config). Awaits poll_interval when idle.
        Set max_iterations to bound the loop (useful for tests / cron-style runs).
        """
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            iterations += 1
            delivery = await self.poll()
            if delivery is None:
                await asyncio.sleep(poll_interval)
                continue
            try:
                result = handler(delivery)
                if inspect.isawaitable(result):
                    await result
                if auto_complete:
                    await self.complete(delivery["id"], remark="ok")
            except Exception as exc:  # noqa: BLE001
                await self.fail(delivery["id"], remark=str(exc)[:500])
