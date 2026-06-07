"""Admin API routes — require the admin role."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.core.security import require_admin
from app.database import get_session
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.common import Page

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/users", response_model=Page[UserOut])
async def list_users(
    page: Pagination = Depends(),
    _admin: Annotated[User, Depends(require_admin)] = None,
    session: AsyncSession = Depends(get_session),
):
    """List all users (admin only)."""
    from sqlalchemy import func

    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    rows = (
        await session.execute(
            select(User).order_by(User.created_at.desc()).limit(page.limit).offset(page.offset)
        )
    ).scalars().all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)
