"""FlowQueue admin CLI.

    python -m app.cli create-user --email a@b.com --password secret [--admin]
    python -m app.cli promote-admin --email a@b.com
    python -m app.cli create-api-key --name dev --email a@b.com
    python -m app.cli claim-orphans --email a@b.com
    python -m app.cli init-db
"""

import asyncio

import click
from sqlalchemy import select

from app.core.security import generate_api_key, hash_password
from app.database import async_session_factory, engine
from app.models.api_key import ApiKey
from app.models.queue import Queue
from app.models.user import User, UserRole


@click.group()
def cli() -> None:
    """FlowQueue management commands."""


async def _get_user(session, email: str) -> User:
    user = (
        await session.execute(select(User).where(User.email == email.lower()))
    ).scalar_one_or_none()
    if user is None:
        raise click.ClickException(f"No user with email {email}")
    return user


@cli.command("create-user")
@click.option("--email", required=True)
@click.option("--password", required=True)
@click.option("--admin", is_flag=True, default=False, help="Grant admin role.")
def create_user(email: str, password: str, admin: bool) -> None:
    """Create a user account."""

    async def _run() -> None:
        async with async_session_factory() as session:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                role=UserRole.admin if admin else UserRole.user,
            )
            session.add(user)
            await session.commit()

    asyncio.run(_run())
    click.echo(f"User created: {email} ({'admin' if admin else 'user'})")


@cli.command("promote-admin")
@click.option("--email", required=True)
def promote_admin(email: str) -> None:
    """Promote an existing user to admin."""

    async def _run() -> None:
        async with async_session_factory() as session:
            user = await _get_user(session, email)
            user.role = UserRole.admin
            await session.commit()

    asyncio.run(_run())
    click.echo(f"{email} is now an admin.")


@cli.command("create-api-key")
@click.option("--name", required=True, help="Human-readable label for the key.")
@click.option("--email", required=True, help="Owning user's email.")
def create_api_key(name: str, email: str) -> None:
    """Create an API key for a user and print the raw token ONCE."""

    async def _run() -> str:
        raw, prefix, key_hash = generate_api_key()
        async with async_session_factory() as session:
            user = await _get_user(session, email)
            session.add(
                ApiKey(name=name, prefix=prefix, key_hash=key_hash, user_id=user.id)
            )
            await session.commit()
        return raw

    token = asyncio.run(_run())
    click.echo(f"API key created (name={name}, owner={email}).")
    click.echo(f"TOKEN (save now, shown once): {token}")


@cli.command("claim-orphans")
@click.option("--email", required=True, help="User to assign all orphan queues/keys to.")
def claim_orphans(email: str) -> None:
    """Assign pre-tenancy (NULL-owner) queues and API keys to a user."""

    async def _run() -> tuple[int, int]:
        async with async_session_factory() as session:
            user = await _get_user(session, email)
            queues = (
                await session.execute(select(Queue).where(Queue.owner_id.is_(None)))
            ).scalars().all()
            keys = (
                await session.execute(select(ApiKey).where(ApiKey.user_id.is_(None)))
            ).scalars().all()
            for q in queues:
                q.owner_id = user.id
            for k in keys:
                k.user_id = user.id
            await session.commit()
            return len(queues), len(keys)

    nq, nk = asyncio.run(_run())
    click.echo(f"Assigned {nq} queue(s) and {nk} API key(s) to {email}.")


@cli.command("init-db")
def init_db() -> None:
    """Create all tables directly from models (alternative to alembic upgrade)."""

    async def _run() -> None:
        from app.database import Base
        import app.models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_run())
    click.echo("Database tables created.")


if __name__ == "__main__":
    cli()
