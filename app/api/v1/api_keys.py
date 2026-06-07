"""API key routes — create/list/revoke keys scoped to the current user."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import generate_api_key, get_principal
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

Principal = Annotated[User, Depends(get_principal)]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate, user: Principal, session: AsyncSession = Depends(get_session)
):
    """Mint a new API key owned by the current user. Raw token returned ONCE."""
    raw, prefix, key_hash = generate_api_key()
    scopes = [s for s in data.scopes if s in ("publish", "consume", "admin")] or ["publish", "consume"]
    key = ApiKey(
        name=data.name, prefix=prefix, key_hash=key_hash, user_id=user.id, scopes=scopes
    )
    session.add(key)
    await session.flush()
    out = ApiKeyOut.model_validate(key)
    return ApiKeyCreated(**out.model_dump(), token=raw)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(user: Principal, session: AsyncSession = Depends(get_session)):
    """List the current user's API keys (admins see all)."""
    stmt = select(ApiKey).order_by(ApiKey.created_at.desc())
    if not user.is_admin:
        stmt = stmt.where(ApiKey.user_id == user.id)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


@router.delete("/{key_id}", response_model=ApiKeyOut)
async def revoke_api_key(
    key_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    key = await session.get(ApiKey, key_id)
    if key is None or (not user.is_admin and key.user_id != user.id):
        raise NotFoundError(f"API key not found: {key_id}")
    key.is_active = False
    await session.flush()
    return key
