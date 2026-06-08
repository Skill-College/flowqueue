# Contributing to FlowQueue

Thanks for your interest in contributing! This document explains how to get a dev
environment running, the conventions we follow, and how to submit changes.

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

The fastest path is Docker Compose (app auto-runs `alembic upgrade head` on start):

```bash
docker compose up -d --build
docker compose exec app python -m app.cli create-user --email dev@x.com --password password123 --admin
```

- UI: http://localhost:5173 · API: http://localhost:8000 · OpenAPI docs: `/docs`

### Local development without Docker

```bash
pip install -e ".[dev]"
export DATABASE_URL=postgresql+asyncpg://flow:flow@localhost:5432/flowqueue
alembic upgrade head
uvicorn app.main:app --reload          # API
python -m app.workers.runner           # workers (separate shell)
pytest                                  # tests
```

You need a running PostgreSQL for migrations and tests. See the
[README](README.md#local-development-without-docker) for full details, and
[AGENTS.md](AGENTS.md) for a directory map and architecture overview.

## Project layout

- `app/` — FastAPI backend (routes, services, workers, SDK, CLI)
- `sdk/` — standalone Python client SDK (published to PyPI as `flowqueue`)
- `web/` — React + Vite + TypeScript SPA
- `alembic/` — database migrations
- `tests/` — backend test suite

## Making changes

1. Fork the repo and create a feature branch off `main`
   (e.g. `feat/replay-pagination` or `fix/visibility-timeout`).
2. Make your change. Keep it focused — one logical change per PR.
3. Add or update tests for any behavior change.
4. Run the test suite locally:
   ```bash
   pytest
   ```
5. If you changed the database schema, generate a migration:
   ```bash
   alembic revision --autogenerate -m "describe change"
   ```
6. Open a pull request against `main` and fill out the PR template.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/). Common prefixes:

- `feat:` — a new feature
- `fix:` — a bug fix
- `chore:` — tooling, deps, or housekeeping
- `docs:` — documentation only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or fixing tests

Example: `feat: add cursor pagination to replay history`

## Code style

- Python 3.11+, async-first (SQLAlchemy 2 asyncpg, FastAPI async routes).
- Type hints everywhere; Pydantic v2 models for I/O.
- Keep new code consistent with surrounding patterns — match naming and structure.

## Reporting bugs and requesting features

Use the issue templates (Bug report / Feature request). For security issues, **do not**
open a public issue — follow [SECURITY.md](SECURITY.md).
