# AGENTS.md — FlowQueue

Onboarding for AI agents (and humans) working in this repo. Read this first.

## What this is
FlowQueue — a cloud-native message processing platform: durable queues, per-consumer
delivery lifecycle (retries, visibility timeout, dead-letter), scheduled delivery,
webhooks with conditional filter rules + HMAC signing, replay/backfill, realtime SSE,
metrics, multi-tenant users, and a tamper-evident append-only audit log. **No Redis** —
everything is Postgres-backed.

## Stack
- Backend: FastAPI (async), SQLAlchemy 2 (asyncpg), Alembic, Pydantic v2, APScheduler,
  httpx, PyJWT, bcrypt, structlog. Python 3.11+.
- Frontend: React 18 + Vite + TypeScript + Tailwind + TanStack Query + React Router
  + recharts + sonner (`web/`).
- SDK: standalone sync httpx client, published to PyPI as `flowqueue` (`sdk/`).
- Infra: Docker Compose — `db` (Postgres 18), `app` (uvicorn API), `worker`
  (APScheduler jobs), `web` (nginx serves SPA + proxies `/api` → app). Optional `nginx`.

## Run it
```bash
docker compose up -d --build          # db, app, worker, web (+nginx)
# app auto-runs `alembic upgrade head` on start
docker compose exec app python -m app.cli create-user --email a@b.com --password password123 --admin
```
- UI: http://localhost:5173  · API: http://localhost:8000  · OpenAPI: /docs · /health · /metrics
- First registered user becomes **admin**.

## Directory map
```
app/
  main.py            FastAPI app, CORS, exception handlers, /health, /metrics
  config.py          pydantic-settings (env)
  database.py        async engine + session, declarative Base
  core/
    security.py      passwords, API keys, JWT, get_principal, require_admin,
                     require_scope, SSRF validate_endpoint_url
    authz.py         authorize_queue/consumer/delivery/replay (ownership → 404)
    routing_engine.py  matches(rules, payload, mode) filter evaluator (no eval)
    exceptions.py    FlowQueueError + handlers (404/409/422/403/401)
  models/            SQLAlchemy: queue, consumer, message, delivery, delivery_log,
                     queue_log, replay_request, api_key, user, queue_sequence
  schemas/           Pydantic request/response
  services/          audit_service (delivery audit chokepoint), queue_audit_service
                     (queue timeline chokepoint), queue/consumer/message/
                     delivery/webhook/replay/auth services
  api/v1/            routers: auth, admin, queues, consumers, messages, deliveries,
                     replay, stats(search), api_keys, events(SSE+timeseries)
  workers/           runner (APScheduler) + visibility_reclaim, webhook_dispatcher,
                     retention_janitor, replay_worker
  cli.py             create-user, promote-admin, create-api-key, claim-orphans, init-db
alembic/versions/    migrations 0001..0008
web/                 React SPA (src/pages, src/components/ui, src/lib)
sdk/                 publishable `flowqueue` client (+ PUBLISHING.md)
```

## Non-negotiable invariants (do not break)
1. **Audit log in the same transaction.** Every delivery state change goes through
   `app/services/audit_service.py` and writes a `delivery_logs` row in the SAME
   session/txn as the mutation. Never mutate delivery status without a log.
2. **delivery_logs are append-only.** Never UPDATE/DELETE them. Retention nulls the FK
   (`ON DELETE SET NULL`) so logs survive message/delivery purge. **queue_logs** follow
   the same rule: every queue lifecycle action (create/update/pause/resume/archive/
   restore/purge) writes one row via `app/services/queue_audit_service.py` in the SAME
   txn as the change; append-only, FK `ON DELETE SET NULL`.
3. **Tenant isolation.** Every queue-scoped route resolves ownership via
   `app/core/authz.py` (returns 404, not 403, for non-owners). Admins bypass. List
   endpoints filter by `owner_id`. Workers are system-level (no ownership filter) but
   skip inactive consumers / paused / archived queues.
4. **SSRF guard.** Webhook endpoint URLs are validated (`validate_endpoint_url`) on
   create/update AND re-validated at dispatch. Private/loopback/link-local blocked.
5. **Scheduler only in the worker container** (`RUN_WORKERS=1`), never in app workers.
6. **API-key scopes**: `publish` (POST messages), `consume` (poll/ack/complete/fail/
   remark). JWT/UI users get all scopes. Enforced via `require_scope`.

## Conventions / gotchas
- `metadata` is reserved by SQLAlchemy Declarative → models map Python attr `meta` to
  the DB column `"metadata"`. Pydantic OUT schemas alias `meta` → `metadata`.
- Models that get UPDATEd with server/onupdate defaults set
  `__mapper_args__ = {"eager_defaults": True}` (Queue, Delivery) so sync serialization
  doesn't trigger a lazy reload (`MissingGreenlet`).
- Per-queue `sequence_num` via `queue_sequences` row + `SELECT ... FOR UPDATE` in the
  publish txn (gapless).
- `max_retries` = max TOTAL delivery attempts.
- Delivery states: pending → processing → completed | failed | **dead** (DLQ).
- Concurrency: pollers/workers use `FOR UPDATE SKIP LOCKED`. Pull (`poll_next`) only
  serves `http`/`sdk` consumers; webhook deliveries are owned by `webhook_dispatcher`.
- Webhook `custom_headers`: merged in `webhook_service._post` as
  `{Content-Type, **custom_headers, **reserved X-FlowQueue-*, signature}` — reserved and
  signature headers always win (callers can't override/forge them).
- Purge (`POST /queues/{id}/purge`, `queue_service.purge_queue`): hard-deletes only
  `pending` deliveries + messages left with zero deliveries; never touches
  processing/completed/failed/dead; does NOT reset `queue_sequences`.
- Retention is outcome-based (`retention_janitor`): `success_retention_seconds` (all
  deliveries completed) vs `failed_retention_seconds` (any failed/dead) vs
  `retention_seconds` (pending/`expires_at`). Mixed outcome → failed bucket. Each sweep
  writes a `messages_expired` queue_log row (counts in `context`); `/metrics` sums them
  into `flowqueue_messages_purged_total{outcome}`. `processed_retention_seconds` is gone
  (renamed → `success_retention_seconds` in migration 0008).
- Realtime SSE (`/api/v1/events/stream`) takes the access token as a **query param**
  (EventSource can't set headers); it polls delivery_logs for owned queues.

## Adding a migration
Use Alembic. To add an enum value, **recreate the type** (rename → create new →
`ALTER COLUMN ... TYPE ... USING ...::text::newtype` → drop old) — Postgres can't
`ADD VALUE` inside a txn reliably. See `alembic/versions/0003` / `0005` for the pattern.
Migrations run automatically via the `app` container command.

## Testing & build
- Backend: `python -m pytest -q` (unit tests in `tests/`: routing engine, retry/DLQ
  logic, webhook signing). SDK: `python -m pytest sdk/tests`.
- Frontend: `cd web && npm run build` (tsc + vite) must be clean before deploy.
- After backend changes: `docker compose up -d --build app worker`. After web:
  `docker compose up -d --build web`. Confirm `docker compose exec app alembic current`.

## SDK / PyPI
`sdk/` is the published `flowqueue` client. Publish via Trusted Publishing — see
`sdk/PUBLISHING.md`. The server distribution is named `flowqueue-server` (root
pyproject) so the PyPI name `flowqueue` belongs to the SDK.

## History
Full design + decisions + phase log live in the plan file:
`~/.claude/plans/you-are-building-a-glowing-flute.md` (Phases 1–6). When in doubt about
*why* something is shaped a certain way, check there.
