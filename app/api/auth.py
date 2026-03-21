from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, decode_token
from app.schemas.auth import LoginRequest, TokenResponse
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


from fastapi.responses import JSONResponse

@router.post("/login")
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # ❗ КЛЮЧЕВАЯ ПРОВЕРКА
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(str(user.id))

    response = JSONResponse({
        "access_token": token
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24
    )

    return response