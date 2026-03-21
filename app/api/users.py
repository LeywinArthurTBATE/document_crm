from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.core.security import hash_password
from app.models.permission import Role
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.code != "ADMIN":
        raise HTTPException(403, "Not enough permissions")

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "User already exists")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role_id=data.role_id
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 🔥 фикс MissingGreenlet
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user.id)
    )

    return result.scalar_one()

@router.get("", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.is_active == True)
    )
    return result.scalars().all()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == current_user.id)
    )

    return result.scalar_one()

@router.get("/roles")
async def get_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # можно оставить только для админа
    if current_user.role.code != "ADMIN":
        raise HTTPException(403, "Not enough permissions")

    result = await db.execute(select(Role))
    roles = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "code": r.code
        }
        for r in roles
    ]

@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # только админ
    if current_user.role.code != "ADMIN":
        raise HTTPException(403, "Not enough permissions")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # нельзя удалить самого себя (важно)
    if user.id == current_user.id:
        raise HTTPException(400, "You cannot deactivate yourself")

    user.is_active = False

    await db.commit()

    return {"status": "deactivated"}

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.code != "ADMIN":
        raise HTTPException(403, "Not enough permissions")

    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # обновления
    if data.email:
        user.email = data.email

    if data.full_name:
        user.full_name = data.full_name

    if data.role_id:
        user.role_id = data.role_id

    if data.password:
        user.password_hash = hash_password(data.password)

    await db.commit()
    await db.refresh(user)

    return user