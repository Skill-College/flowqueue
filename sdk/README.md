# flowqueue

Python client SDK for **FlowQueue** — a cloud-native message processing platform
(durable queues, per-consumer delivery lifecycle, retries, dead-letter queue,
scheduled delivery, webhooks with HMAC signing, replay, and a tamper-evident audit
log).

```bash
pip install flowqueue
```

## Quickstart

```python
from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("https://flowqueue.example.com", "fq_your_api_key")

# Create a queue + a pull consumer
queue = client.create_queue("orders", max_retries=5, dlq_enabled=True)
consumer = client.create_consumer(queue["id"], "billing", type="http")

# Publish (optionally scheduled)
client.publish(queue["id"], {"order_id": 42}, idempotency_key="order-42")
client.publish(queue["id"], {"order_id": 43}, delay_seconds=30)   # deliver in 30s

# Consume one delivery
c = FlowQueueConsumer(client, consumer["id"])
d = c.poll()
if d:
    print(d.payload)
    c.complete(d.id, remark="done")
```

## Run a worker loop

```python
def handle(delivery):
    process(delivery.payload)        # raise to fail (retry / DLQ), return to complete

FlowQueueConsumer(client, consumer_id).run(handle, poll_interval=2.0)
```

## Management, replay, DLQ

```python
client.pause_queue(qid); client.resume_queue(qid)
client.queue_stats(qid)
client.purge_queue(qid)              # permanently delete pending messages
client.queue_timeline(qid, action="queue_purged")  # queue activity log
client.replay_failed(consumer_id)
dead = client.dlq_list(qid)
client.requeue_all(qid)              # bulk requeue the dead-letter queue

# Webhook consumer with validation headers + outcome-based retention queue:
q = client.create_queue("billing", success_retention_seconds=86400,
                        failed_retention_seconds=604800)
client.create_consumer(q["id"], "hook", type="webhook",
                       endpoint_url="https://example.com/hook",
                       custom_headers={"X-Api-Key": "secret"})
```

## API keys & scopes

Generate scoped keys in the FlowQueue UI or:

```python
key = client.create_api_key("ci-publisher", scopes=["publish"])
print(key["token"])   # shown once
```

Errors raise `flowqueue.ApiError(status, code, message)`.

## License

MIT
