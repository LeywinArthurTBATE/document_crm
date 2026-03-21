from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None

    # 1. Header (API)
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]

    # 2. Cookie (SSR)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("sub")

    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )

    user = result.scalar_one_or_none()
    if not user.is_active:
        raise HTTPException(403, "User is deactivated")
    if not user:
        raise HTTPException(401, "User not found")

    return user

from fastapi import Request

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_current_user(request, db)
    except:
        return None