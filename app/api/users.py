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

# app/api/users.py (добавить в конец файла)
from app.models.notification import Notification
from sqlalchemy import update as sql_update

@router.get("/me/notifications")
async def get_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "entity_id": n.entity_id,
            "is_read": n.is_read,
            "created_at": n.created_at,
            "document_title": n.document_title,
            "actor_name": n.actor_name,
            "message_text": n.message_text,
            "extra_data": n.extra_data,
        }
        for n in notifications
    ]


@router.patch("/me/notifications/{notification_id}")
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(404, "Notification not found")
    notification.is_read = True
    await db.commit()
    return {"status": "read"}


@router.patch("/me/notifications/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        sql_update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return {"status": "all read"}