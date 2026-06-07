"""Feedback API routes — public submit, admin list."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.exceptions import AuthError
from app.core.security import decode_token, require_admin
from app.database import get_session
from app.models.user import User
from app.schemas.common import Page
from app.schemas.feedback import FeedbackCreate, FeedbackOut
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])

_optional_bearer = HTTPBearer(auto_error=False)


async def optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_optional_bearer)],
    session: AsyncSession = Depends(get_session),
):
    """Best-effort principal resolution. Returns a user id for a valid JWT, else None.

    Feedback is public, so a missing/invalid token must not fail the request — we
    only use it to attribute the submission when the visitor happens to be logged in.
    """
    if credentials is None or not credentials.credentials:
        return None
    token = credentials.credentials
    if token.startswith("fq_"):
        return None
    try:
        user_id = decode_token(token, expected_type="access")
    except AuthError:
        return None
    user = await session.get(User, user_id)
    return user.id if user and user.is_active else None


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    data: FeedbackCreate,
    user_id=Depends(optional_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Submit product feedback (public; no auth required)."""
    return await feedback_service.create_feedback(session, data, user_id=user_id)


@router.get("", response_model=Page[FeedbackOut], dependencies=[Depends(require_admin)])
async def list_feedback(
    page: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """List submitted feedback (admin only)."""
    items, total = await feedback_service.list_feedback(session, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)
