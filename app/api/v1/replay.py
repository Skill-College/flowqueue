"""Replay API routes (owner-scoped)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import authorize_consumer, authorize_replay
from app.core.security import get_principal
from app.database import get_session
from app.models.user import User
from app.schemas.replay import ReplayOut, ReplayRangeRequest, ReplaySelectedRequest
from app.services import replay_service

router = APIRouter(tags=["replay"])

Principal = Annotated[User, Depends(get_principal)]


@router.post(
    "/consumers/{consumer_id}/replay/failed",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_failed(
    consumer_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_consumer(session, consumer_id, user)
    return await replay_service.replay_failed(session, consumer_id)


@router.post(
    "/consumers/{consumer_id}/replay/range",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_range(
    consumer_id: uuid.UUID,
    body: ReplayRangeRequest,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    return await replay_service.replay_range(session, consumer_id, body.from_ts, body.to_ts)


@router.post(
    "/consumers/{consumer_id}/replay/selected",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_selected(
    consumer_id: uuid.UUID,
    body: ReplaySelectedRequest,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    await authorize_consumer(session, consumer_id, user)
    return await replay_service.replay_selected(session, consumer_id, body.message_ids)


@router.post(
    "/consumers/{consumer_id}/replay/backfill",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_backfill(
    consumer_id: uuid.UUID, user: Principal, session: AsyncSession = Depends(get_session)
):
    await authorize_consumer(session, consumer_id, user)
    return await replay_service.replay_backfill(session, consumer_id)


@router.get("/replay/{replay_request_id}", response_model=ReplayOut)
async def get_replay(
    replay_request_id: uuid.UUID,
    user: Principal,
    session: AsyncSession = Depends(get_session),
):
    return await authorize_replay(session, replay_request_id, user)
