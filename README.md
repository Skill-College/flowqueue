# FlowQueue

Cloud-native message processing platform. Durable queues, per-consumer delivery
lifecycle with retries + visibility timeouts, conditional webhook routing, replay /
backfill, and a tamper-evident append-only audit log. FastAPI + PostgreSQL (async
SQLAlchemy) + Docker. No Redis.

## Stack

- FastAPI (async), Uvicorn (`--workers 4`)
- PostgreSQL 15, SQLAlchemy 2 (asyncpg), Alembic
- APScheduler background workers (separate container)
- Pydantic v2, structlog JSON logging, bcrypt API keys
- Python 3.11+

## Architecture

| Component | Role |
|-----------|------|
| `app` container | FastAPI HTTP API (uvicorn, 4 workers) |
| `worker` container | APScheduler running all background jobs (only here) |
| `db` container | PostgreSQL with a named volume |
| `nginx` container | reverse proxy + TLS termination template |

### Background workers

| Worker | Interval | Job |
|--------|----------|-----|
| `visibility_reclaim` | 10s | reclaim stuck `processing` deliveries (retry/fail) |
| `webhook_dispatcher` | 5s | push pending deliveries to webhook/workflow consumers |
| `replay_worker` | 2s | process replay jobs (≤100 msg/s) |
| `retention_janitor` | 1h | purge expired, fully-terminal messages |

### Delivery lifecycle

```
pending ──poll/ack──> processing ──complete──> completed
   ^                       │
   └────retry (attempt++)──┴──fail/timeout──> failed (after max_retries)
```

Every state transition writes a row to `delivery_logs` **in the same transaction**
(`app/services/audit_service.py`). `delivery_logs` is append-only and never deleted —
when retention purges a message/delivery, the FK `ON DELETE SET NULL` keeps the log
rows; the log body preserves the trail.

## Quickstart

```bash
# 1. Build and start everything (app auto-runs `alembic upgrade head`).
docker compose up --build -d

# 2. Mint the first API key (bootstrap — the API's create-key endpoint needs a key).
docker compose exec app python -m app.cli create-api-key --name dev
#   -> TOKEN (save now, shown once): fq_xxxxxxxx...

export TOKEN=fq_xxxxxxxx...
export BASE=http://localhost:8000

# 3. Create a queue.
QUEUE=$(curl -s -X POST $BASE/api/v1/queues \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"orders","max_retries":3,"visibility_timeout_seconds":30}' | jq -r .id)

# 4. Add an HTTP (pull) consumer.
CONSUMER=$(curl -s -X POST $BASE/api/v1/queues/$QUEUE/consumers \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"billing","type":"http"}' | jq -r .id)

# 5. Publish a message (idempotency_key optional).
curl -s -X POST $BASE/api/v1/queues/$QUEUE/messages \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"payload":{"order_id":42,"amount":1500},"idempotency_key":"order-42"}'

# 6. Poll, then complete.
DELIVERY=$(curl -s -X POST $BASE/api/v1/consumers/$CONSUMER/poll \
  -H "Authorization: Bearer $TOKEN" | jq -r .id)
curl -s -X POST $BASE/api/v1/deliveries/$DELIVERY/complete \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"remark":"processed"}'

# 7. Inspect the audit trail.
curl -s $BASE/api/v1/deliveries/$DELIVERY/history -H "Authorization: Bearer $TOKEN"
```

Interactive docs: `http://localhost:8000/docs` (unauthenticated). Health:
`http://localhost:8000/health`.

## Conditional routing (webhook/workflow consumers)

`routing_rules` is a JSONB array on the consumer; first matching rule wins, else
`endpoint_url` is used. No `eval` — deterministic evaluation in
`app/core/routing_engine.py`.

```json
[
  {"field": "payload.country", "operator": "equals", "value": "IN",
   "action_url": "https://api-india.example.com/hook"},
  {"field": "payload.amount", "operator": "greater_than", "value": 1000,
   "action_url": "https://high-value.example.com/hook"}
]
```

Operators: `equals`, `not_equals`, `contains`, `greater_than`, `less_than`.
Endpoint and rule URLs are SSRF-checked (private/loopback/link-local IPs blocked).

## Replay

```bash
# Replay all failed deliveries for a consumer (returns a replay job).
curl -X POST $BASE/api/v1/consumers/$CONSUMER/replay/failed -H "Authorization: Bearer $TOKEN"
# Other modes: /replay/range {from_ts,to_ts}, /replay/selected {message_ids}, /replay/backfill
# Poll job status:
curl $BASE/api/v1/replay/<replay_request_id> -H "Authorization: Bearer $TOKEN"
```

## Python SDK

```python
from app.sdk import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("http://localhost:8000", "fq_...")
client.publish(queue_id, {"order_id": 42}, idempotency_key="order-42")

consumer = FlowQueueConsumer(client, consumer_id)
d = consumer.poll()
if d:
    try:
        handle(d.payload)
        consumer.complete(d.id, remark="ok")
    except Exception as e:
        consumer.fail(d.id, remark=str(e))
```

## Configuration (env vars)

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://flow:flow@db:5432/flowqueue` | must use `asyncpg` |
| `SECRET_KEY` | `change-me-in-prod` | set in production |
| `API_KEY_HEADER` | `Authorization` | bearer token header |
| `LOG_LEVEL` | `INFO` | |
| `WORKER_CONCURRENCY` | `4` | |
| `RUN_WORKERS` | `0` | `1` in the worker container |

## Local development (without Docker)

```bash
pip install -e ".[dev]"
export DATABASE_URL=postgresql+asyncpg://flow:flow@localhost:5432/flowqueue
alembic upgrade head
python -m app.cli create-api-key --name dev
uvicorn app.main:app --reload          # API
python -m app.workers.runner           # workers (separate shell)
pytest                                  # tests
```

## Auth

Bearer token in `Authorization`. Keys are stored bcrypt-hashed in `api_keys`
(only a short non-secret prefix is indexed for lookup). All `/api/v1/*` routes
require a valid key; `/health` and `/docs` do not. Bootstrap the first key with the
CLI, then mint more via `POST /api/v1/api-keys`.
