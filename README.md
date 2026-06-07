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

## Web UI & user accounts

A React + Vite + Tailwind SPA lives in `web/` and runs as its own container
(`web`, nginx) that serves the build and proxies `/api` to the `app` service
(single origin → no CORS, refresh cookie works).

- **Open**: http://localhost:5173
- **Multi-tenancy**: every queue is owned by a user. A user sees only their own
  queues + everything nested under them. The **first registered account becomes
  admin** (can see/manage all). Self-signup is open.
- **Auth**: email + password → JWT access token (held in memory) + refresh token
  (httpOnly cookie). API keys are scoped to the creating user and authenticate AS
  that user (so SDK/programmatic access respects the same isolation).

### Pages
Dashboard (aggregate stats + chart), Queues (list/create), Queue detail
(config + stats + Messages/Consumers tabs + publish dialog), Consumer detail
(deliveries, poll, replay/backfill), Delivery detail (audit-log timeline with
ack/complete/fail/remark), API Keys (create/revoke, token shown once), Admin →
Users (admin only).

### User CLI
```bash
docker compose exec app python -m app.cli create-user --email a@b.com --password secret --admin
docker compose exec app python -m app.cli promote-admin --email a@b.com
docker compose exec app python -m app.cli create-api-key --name dev --email a@b.com
docker compose exec app python -m app.cli claim-orphans --email a@b.com   # assign pre-tenancy data
```

## Quickstart

```bash
# 1. Build and start everything (app auto-runs `alembic upgrade head`).
docker compose up --build -d

# 2. Create a user (first user becomes admin), then mint an API key for it.
docker compose exec app python -m app.cli create-user --email dev@x.com --password password123 --admin
docker compose exec app python -m app.cli create-api-key --name dev --email dev@x.com
#   -> TOKEN (save now, shown once): fq_xxxxxxxx...
# (Or just open http://localhost:5173 and register in the UI.)

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

## Consumer types

| Type | Mode | How it gets work |
|------|------|------------------|
| `http` | pull | `POST /consumers/{id}/poll` claims the next delivery; then `complete`/`fail` |
| `sdk` | pull | same as http, via the Python SDK (`FlowQueueConsumer`) |
| `webhook` | push | `webhook_dispatcher` POSTs the payload to `endpoint_url` (routing-rule aware) |

(`workflow` was removed — conditional push by payload is webhook `routing_rules`.)

### Webhook `auto_complete`
- **on** (default): HTTP 2xx → delivery `completed`; non-2xx → retry/fail.
- **off**: 2xx leaves the delivery `processing`; your receiver must call back
  `POST /deliveries/{id}/complete` (or `/fail`) using the `X-FlowQueue-Delivery-ID`
  header. No callback before the visibility timeout → redelivered, then `failed` at
  max retries. The consumer detail page shows copy-paste demo code per type.

## Delivery filter rules (webhook consumers)

`routing_rules` is a JSONB array of **filter conditions** on the consumer — they
decide whether to deliver to the single `endpoint_url` (not multi-URL routing).
`match_mode` is `any` (deliver if any rule matches) or `all` (deliver only if all
match). No rules → always deliver. A message that matches no rule is **skipped** and
its delivery marked `completed` (filtered). Deterministic, no `eval`
(`app/core/routing_engine.py`).

```json
{
  "match_mode": "all",
  "routing_rules": [
    {"field": "payload.country", "operator": "equals", "value": "IN"},
    {"field": "payload.amount", "operator": "greater_than", "value": 1000}
  ]
}
```

Operators: `equals`, `not_equals`, `contains`, `greater_than`, `less_than`.
The `endpoint_url` is SSRF-checked (private/loopback/link-local IPs blocked).

## Queues: publish guard, archive & restore

- **Publish guard**: publishing to a queue with **zero active consumers** is rejected
  with `409` — add/enable a consumer first (prevents orphan messages).
- **Archive**: `DELETE /queues/{id}` soft-archives (`is_active=false`). Archived
  queues reject publish. The UI Queues page has **Active** / **Archived** tabs.
- **Restore**: `PATCH /queues/{id}` `{"is_active": true}` (Restore button in the UI).

## UI theme

Light/dark toggle in the sidebar (persisted to `localStorage`), bold Duolingo-style
palette (green primary, high-contrast). Defaults to dark.

## Enable / disable a consumer

Deactivate: `DELETE /queues/{qid}/consumers/{cid}` (sets `is_active=false`).
Re-enable: `PATCH /queues/{qid}/consumers/{cid}` with `{"is_active": true}`. The
consumer detail page has an Enable/Disable toggle. Inactive consumers receive no new
deliveries on publish.

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
