"""FlowQueue admin CLI.

Bootstraps the first API key (the API's POST /api-keys requires an existing key)
and offers a DB init helper.

    python -m app.cli create-api-key --name dev
    python -m app.cli init-db
"""

import asyncio

import click

from app.core.security import generate_api_key
from app.database import async_session_factory, engine
from app.models.api_key import ApiKey


@click.group()
def cli() -> None:
    """FlowQueue management commands."""


@cli.command("create-api-key")
@click.option("--name", required=True, help="Human-readable label for the key.")
def create_api_key(name: str) -> None:
    """Create an API key and print the raw token ONCE (it is not recoverable)."""

    async def _run() -> str:
        raw, prefix, key_hash = generate_api_key()
        async with async_session_factory() as session:
            session.add(ApiKey(name=name, prefix=prefix, key_hash=key_hash))
            await session.commit()
        return raw

    token = asyncio.run(_run())
    click.echo(f"API key created (name={name}).")
    click.echo(f"TOKEN (save now, shown once): {token}")


@cli.command("init-db")
def init_db() -> None:
    """Create all tables directly from models (alternative to alembic upgrade)."""

    async def _run() -> None:
        from app.database import Base
        import app.models  # noqa: F401  (register tables)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_run())
    click.echo("Database tables created.")


if __name__ == "__main__":
    cli()
