"""API key hashing/verification, auth dependency, and SSRF URL validation."""

import ipaddress
import secrets
import socket
from urllib.parse import urlparse

import bcrypt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, SSRFError
from app.database import get_session
from app.models.api_key import ApiKey
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

_PREFIX_LEN = 8

headers = HTTPBearer()


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


def _extract_bearer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(headers)],
) -> str | None:
    token = credentials.credentials
    if not token:
        return None
    return token


async def get_current_api_key(
    request: Request,
    credentials: Annotated[str, Depends(_extract_bearer)],
    session: AsyncSession = Depends(get_session),
) -> ApiKey:
    """FastAPI dependency: authenticate the request via Bearer token.

    Looks up active keys by non-secret prefix, then bcrypt-verifies. Updates
    last_used_at on success. Raises AuthError (401) otherwise.
    """
    if not credentials:
        raise AuthError("Missing or malformed Authorization header")

    prefix = credentials[:_PREFIX_LEN]
    rows = (
        (
            await session.execute(
                select(ApiKey).where(
                    ApiKey.prefix == prefix, ApiKey.is_active.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )

    for key in rows:
        if verify_token(credentials, key.key_hash):
            from sqlalchemy import func

            key.last_used_at = func.now()
            return key

    raise AuthError("Invalid API key")


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
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")

    # Resolve all addresses and ensure none are blocked.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFError(f"Cannot resolve host {host!r}") from exc

    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise SSRFError(f"Endpoint host resolves to forbidden address: {ip}")
