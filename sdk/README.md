# flowqueue

Async, typed Python **runtime** client for **FlowQueue** — a cloud-native message
processing platform. The SDK does two things: **publish** messages and **consume**
deliveries. Everything else (creating queues/consumers, API keys, replay, dead-letter
recovery, metrics) lives in the **FlowQueue UI** (or the HTTP API directly).

```bash
pip install flowqueue
```

Requires Python 3.9+. Ships with type hints (`py.typed`) — editors autocomplete
response shapes (`MessageOut`, `DeliveryOut`).

## Quickstart

Create the queue and consumer in the FlowQueue UI, then use their ids here:

```python
import asyncio
from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

QUEUE_ID = "<queue_id>"
CONSUMER_ID = "<consumer_id>"


async def main():
    async with AsyncFlowQueueClient("https://flowqueue.example.com", "fq_your_api_key") as client:
        # Publish (optionally scheduled)
        await client.publish(QUEUE_ID, {"order_id": 42}, idempotency_key="order-42")
        await client.publish(QUEUE_ID, {"order_id": 43}, delay_seconds=30)  # deliver in 30s

        # Consume one delivery
        consumer = AsyncFlowQueueConsumer(client, CONSUMER_ID)
        d = await consumer.poll()
        if d:
            print(d["payload"])
            await consumer.complete(d["id"], remark="done")


asyncio.run(main())
```

## Run a worker loop

The handler may be sync or async. Return → the delivery is completed; raise → it is
failed (retry / DLQ per queue config).

```python
async def handle(delivery):
    await process(delivery["payload"])

async def main():
    async with AsyncFlowQueueClient(url, key) as client:
        await AsyncFlowQueueConsumer(client, CONSUMER_ID).run(handle, poll_interval=2.0)
```

## Scheduling

```python
from datetime import datetime, timedelta, timezone

await client.publish(qid, {"ping": 1}, delay_seconds=30)
await client.publish(qid, {"ping": 1}, deliver_at=datetime.now(timezone.utc) + timedelta(hours=1))
```

## Errors

Non-2xx responses raise `flowqueue.ApiError(status, code, message)`.

```python
from flowqueue import ApiError

try:
    await client.publish(qid, {"x": 1})
except ApiError as e:
    print(e.status, e.code, e.message)
```

## License

MIT
