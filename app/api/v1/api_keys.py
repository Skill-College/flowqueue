"""API key admin routes — create/list/revoke keys. Guarded by an existing key."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import generate_api_key, get_current_api_key
from app.database import get_session
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(
    prefix="/api-keys", tags=["api-keys"], dependencies=[Depends(get_current_api_key)]
)


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(data: ApiKeyCreate, session: AsyncSession = Depends(get_session)):
    """Mint a new API key. The raw token is returned ONCE and never stored."""
    raw, prefix, key_hash = generate_api_key()
    key = ApiKey(name=data.name, prefix=prefix, key_hash=key_hash)
    session.add(key)
    await session.flush()
    out = ApiKeyOut.model_validate(key)
    return ApiKeyCreated(**out.model_dump(), token=raw)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))).scalars().all()
    return list(rows)


@router.delete("/{key_id}", response_model=ApiKeyOut)
async def revoke_api_key(key_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    key = await session.get(ApiKey, key_id)
    if key is None:
        raise NotFoundError(f"API key not found: {key_id}")
    key.is_active = False
    await session.flush()
    return key
