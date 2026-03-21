from app.core.database import AsyncSessionLocal
from app.models.permission import Permission, Role, RolePermission
from sqlalchemy import select


PERMISSIONS = [
    "document.read",
    "document.create",
    "document.edit",
    "document.edit_deadline",
    "document.assign",
    "document.change_status",
    "document.delete",
    "admin.access",
]


ROLES = {
    "ADMIN": PERMISSIONS,
    "USER": [
        "document.read",
        "document.create",
    ],
    "MANAGER": [
        "document.read",
        "document.create",
        "document.assign",
        "document.change_status",
    ],
}


async def seed():
    async with AsyncSessionLocal() as db:

        # permissions
        perm_map = {}
        for code in PERMISSIONS:
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()

            if not perm:
                perm = Permission(code=code)
                db.add(perm)
                await db.flush()

            perm_map[code] = perm

        # roles
        for role_code, perms in ROLES.items():
            result = await db.execute(select(Role).where(Role.code == role_code))
            role = result.scalar_one_or_none()

            if not role:
                role = Role(code=role_code)
                db.add(role)
                await db.flush()

            for p in perms:
                rp = RolePermission(
                    role_id=role.id,
                    permission_id=perm_map[p].id
                )
                db.add(rp)

        await db.commit()