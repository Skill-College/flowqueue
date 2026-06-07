"""Auth service — registration and login. Issues no tokens itself (routes do that).

First user to register becomes an admin; all subsequent users are regular users.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, ConflictError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    """Create a new user. The very first registered account is made admin.

    Raises ConflictError if the email already exists.
    """
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    role = UserRole.admin if count == 0 else UserRole.user
    user = User(email=email.lower(), password_hash=hash_password(password), role=role)
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(f"Email already registered: {email}") from exc
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    """Verify credentials and return the user. Raises AuthError on failure."""
    user = (
        await session.execute(select(User).where(User.email == email.lower()))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("Account is disabled")
    return user
