"""Security: password hashing, API keys, JWT, auth dependencies, SSRF validation."""

import ipaddress
import secrets
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthError, ForbiddenError, SSRFError
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.user import User

_PREFIX_LEN = 8

# auto_error=False so we can raise our own AuthError (uniform error envelope).
_bearer = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------------- #
# Password hashing (bcrypt; 72-byte input limit handled by truncation guard)
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password."""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# API key generation / hashing
# --------------------------------------------------------------------------- #
def generate_api_key() -> tuple[str, str, str]:
    """Generate a new raw token. Returns (raw_token, prefix, bcrypt_hash)."""
    raw = "fq_" + secrets.token_urlsafe(32)
    prefix = raw[:_PREFIX_LEN]
    key_hash = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    return raw, prefix, key_hash


def verify_token(raw: str, key_hash: str) -> bool:
    """Constant-time bcrypt verification of a raw token against its stored hash."""
    try:
        return bcrypt.checkpw(raw.encode(), key_hash.encode())
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def _create_token(sub: str, token_type: Literal["access", "refresh"], ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id), "access", timedelta(minutes=settings.access_token_ttl_minutes)
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id), "refresh", timedelta(days=settings.refresh_token_ttl_days)
    )


def decode_token(token: str, *, expected_type: str) -> uuid.UUID:
    """Decode and validate a JWT, returning the user id. Raises AuthError on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise AuthError("Wrong token type")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Malformed token subject") from exc


# --------------------------------------------------------------------------- #
# Unified principal resolution (JWT access token OR API key)
# --------------------------------------------------------------------------- #
async def _user_from_api_key(session: AsyncSession, raw: str) -> User:
    prefix = raw[:_PREFIX_LEN]
    rows = (
        await session.execute(
            select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.is_active.is_(True))
        )
    ).scalars().all()
    for key in rows:
        if verify_token(raw, key.key_hash):
            if key.user_id is None:
                raise AuthError("API key is not associated with a user")
            key.last_used_at = func.now()
            user = await session.get(User, key.user_id)
            if user is None or not user.is_active:
                raise AuthError("API key owner is inactive")
            # Scopes granted for this request come from the key.
            user.scopes_granted = list(key.scopes or [])
            return user
    raise AuthError("Invalid API key")


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authenticate the request and return the acting User.

    Accepts either a FlowQueue API key (token starts with ``fq_``) or a JWT access
    token. API keys resolve to their owning user; JWTs resolve via the subject id.
    """
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing or malformed Authorization header")
    token = credentials.credentials

    if token.startswith("fq_"):
        return await _user_from_api_key(session, token)

    user_id = decode_token(token, expected_type="access")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")
    # UI/JWT sessions get all scopes.
    user.scopes_granted = ["publish", "consume", "admin"]
    return user


async def require_admin(user: Annotated[User, Depends(get_principal)]) -> User:
    """Dependency that requires the principal to have the admin role."""
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return user


def require_scope(scope: str):
    """Build a dependency that requires the principal to hold `scope`.

    JWT users have all scopes; API keys are limited to their configured scopes.
    """

    async def _checker(user: Annotated[User, Depends(get_principal)]) -> User:
        granted = getattr(user, "scopes_granted", []) or []
        if scope not in granted and "admin" not in granted:
            raise ForbiddenError(f"API key lacks required scope: {scope}")
        return user

    return _checker


# --------------------------------------------------------------------------- #
# SSRF protection for webhook / workflow endpoint URLs
# --------------------------------------------------------------------------- #
def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # unparseable -> block
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_endpoint_url(url: str) -> None:
    """Raise SSRFError if URL is not http(s) or resolves to a private/loopback IP.

    Blocks 10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, ::1, etc. Called on
    consumer create/update and again at dispatch time.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFError(f"Cannot resolve host {host!r}") from exc

    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise SSRFError(f"Endpoint host resolves to forbidden address: {ip}")
