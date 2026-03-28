from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, create_access_token, decode_token
from app.models import User
from app.schemas.auth import LoginRequest
from app.websocket_manager import manager
from app.core.database import get_db

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

@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
        user = await db.get(User, UUID(user_id))
        if not user or not user.is_active:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    # Подключаем к менеджеру по user_id
    await manager.connect(websocket, f"notifications_{user_id}", str(user.id))
    try:
        while True:
            # Просто держим соединение открытым
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"notifications_{user_id}", str(user.id))