# FlowQueue

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

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
| `retention_janitor` | 1h | permanently delete expired messages (outcome-based windows) |

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
  When `auto_complete=off` and the POST returns 2xx, the delivery's audit timeline
  records a remark naming the webhook consumer that is awaiting the callback.

### Webhook custom headers
Webhook consumers accept a `custom_headers` map (`{"X-Api-Key": "...", ...}`) sent on
**every** POST (and the test delivery), so your receiver can validate the call.
Precedence: caller headers first, then FlowQueue's reserved `X-FlowQueue-*` identity
headers, then `X-FlowQueue-Signature` — so the reserved/signature headers can never be
overridden or forged. Set them via the consumer create/edit dialogs or
`POST/PATCH /queues/{qid}/consumers/{cid}` with `"custom_headers": {...}`.

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

## Queue timeline

Every queue-level action writes an append-only row to `queue_logs`: `queue_created`,
`queue_updated`, `queue_paused`, `queue_resumed`, `queue_archived`, `queue_restored`,
`queue_purged`. Each row carries the action, the actor, an optional remark, and a
JSON `context`. Read it with `GET /queues/{id}/timeline` (paginated; filter with
`?action=queue_purged`). The Queue detail page has a **Timeline** tab with an action
filter. Like `delivery_logs`, the table is append-only and written in the same
transaction as the change (`app/services/queue_audit_service.py`).

## Purge

`POST /queues/{id}/purge` **permanently** deletes all *pending* (un-started) messages:
deliveries still in `pending` status and any message left with no deliveries.
In-flight (`processing`), `completed`, `failed`, and dead-letter messages are kept;
the per-queue sequence counter is not reset. `delivery_logs` survive (their FK is
`ON DELETE SET NULL`). A `queue_purged` timeline row records the counts. The Queue
detail page exposes a **Purge** button behind a confirm dialog. This cannot be undone.

## Message retention (outcome-based)

`retention_janitor` (hourly) **permanently** deletes expired messages. Three per-queue
windows (all editable in the queue create/edit dialogs):

| Window | Applies to | Default |
|--------|------------|---------|
| `retention_seconds` | pending / never-consumed messages (`expires_at` = `published_at` + this) | 604800 (7d) |
| `success_retention_seconds` | messages whose deliveries **all completed** | 86400 (24h) |
| `failed_retention_seconds` | messages with **any** failed/dead delivery (rest terminal) | 604800 (7d) |

A terminal message's age is measured from its newest delivery terminal time
(`completed_at`/`updated_at`). Mixed outcome (some completed, some failed) → **failed
bucket** (kept longer). Deleting a message cascades its deliveries; `delivery_logs`
survive (`ON DELETE SET NULL`).

**Metrics**: each sweep writes a `messages_expired` row to the queue timeline
(`context: {success, failed, total}`), visible/filterable in the **Timeline** tab.
`/metrics` exposes cumulative counters summed from those rows:
```
flowqueue_messages_purged_total{outcome="success"} <n>
flowqueue_messages_purged_total{outcome="failed"} <n>
```

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

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and
guidelines, and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). For security issues, follow
[SECURITY.md](SECURITY.md) — do not open a public issue.

## License

MIT — see [LICENSE](LICENSE). The Python client SDK (`./sdk`, published to PyPI as
`flowqueue`) is also MIT.
