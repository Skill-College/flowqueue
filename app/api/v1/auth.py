"""Auth API routes — register, login, refresh, logout, me.

Access token is returned in the response body (the SPA holds it in memory). The
refresh token is set as an httpOnly cookie so JS cannot read it.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_principal,
)
from app.database import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, user_id) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=create_refresh_token(user_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/",
    )


def _token_response(user_id) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest, response: Response, session: AsyncSession = Depends(get_session)
):
    """Register a new account (first user becomes admin) and log them in."""
    user = await auth_service.register_user(session, data.email, data.password)
    await session.flush()
    _set_refresh_cookie(response, user.id)
    return _token_response(user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)
):
    """Authenticate and issue an access token + refresh cookie."""
    user = await auth_service.authenticate(session, data.email, data.password)
    _set_refresh_cookie(response, user.id)
    return _token_response(user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_session),
    fq_refresh: Annotated[str | None, Cookie()] = None,
):
    """Rotate a fresh access token (and refresh cookie) from the refresh cookie."""
    if not fq_refresh:
        raise AuthError("Missing refresh token")
    user_id = decode_token(fq_refresh, expected_type="refresh")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")
    _set_refresh_cookie(response, user.id)
    return _token_response(user.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Clear the refresh cookie."""
    response.delete_cookie(settings.refresh_cookie_name, path="/")
    return None


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(get_principal)]):
    """Return the currently authenticated user."""
    return user
