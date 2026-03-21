from fastapi import HTTPException
from sqlalchemy import select
from app.models.permission import Permission, UserPermission, RolePermission


async def has_permission(db, user, code: str) -> bool:
    # 1. через роль
    role_perm = await db.execute(
        select(Permission.code)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(
            RolePermission.role_id == user.role_id,
            Permission.code == code,
        )
    )

    if role_perm.scalar_one_or_none():
        return True

    # 2. индивидуальные права
    user_perm = await db.execute(
        select(Permission.code)
        .join(UserPermission, Permission.id == UserPermission.permission_id)
        .where(
            UserPermission.user_id == user.id,
            Permission.code == code,
        )
    )

    return user_perm.scalar_one_or_none() is not None


async def require_permission(db, user, code: str):
    if not await has_permission(db, user, code):
        raise HTTPException(403, f"No permission: {code}")

