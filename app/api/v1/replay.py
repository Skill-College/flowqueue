"""Replay API routes."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_api_key
from app.database import get_session
from app.schemas.replay import ReplayOut, ReplayRangeRequest, ReplaySelectedRequest
from app.services import replay_service

router = APIRouter(tags=["replay"], dependencies=[Depends(get_current_api_key)])


@router.post(
    "/consumers/{consumer_id}/replay/failed",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_failed(consumer_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await replay_service.replay_failed(session, consumer_id)


@router.post(
    "/consumers/{consumer_id}/replay/range",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_range(
    consumer_id: uuid.UUID,
    body: ReplayRangeRequest,
    session: AsyncSession = Depends(get_session),
):
    return await replay_service.replay_range(session, consumer_id, body.from_ts, body.to_ts)


@router.post(
    "/consumers/{consumer_id}/replay/selected",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_selected(
    consumer_id: uuid.UUID,
    body: ReplaySelectedRequest,
    session: AsyncSession = Depends(get_session),
):
    return await replay_service.replay_selected(session, consumer_id, body.message_ids)


@router.post(
    "/consumers/{consumer_id}/replay/backfill",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_backfill(consumer_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await replay_service.replay_backfill(session, consumer_id)


@router.get("/replay/{replay_request_id}", response_model=ReplayOut)
async def get_replay(
    replay_request_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await replay_service.get_replay(session, replay_request_id)
