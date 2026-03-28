from app.core.database import AsyncSessionLocal
from app.models.permission import Permission, Role, RolePermission
from sqlalchemy import select


PERMISSIONS = [
    # --- READ ---
    "document.read",        # свои документы
    "document.read_any",    # любые

    # --- CREATE ---
    "document.create",

    # --- EDIT ---
    "document.edit",        # свои
    "document.edit_any",    # любые

    # --- DELETE ---
    "document.delete",      # свои
    "document.delete_any",  # любые

    # --- ASSIGN ---
    "document.assign",      # свои
    "document.assign_any",  # любые

    # --- STATUS ---
    "document.change_status",
    "document.change_status_any",

    # --- SPECIAL ---
    "document.edit_deadline",

    # --- SYSTEM ---
    "admin.access",
]


ROLES = {
    "ADMIN": PERMISSIONS,

    "USER": [
        "document.read",
        "document.create",
        "document.edit",
        "document.delete",
        "document.change_status",
    ],

    "MANAGER": [
        "document.read",
        "document.read_any",

        "document.create",

        "document.edit",
        "document.edit_any",

        "document.assign",
        "document.assign_any",

        "document.change_status",
        "document.change_status_any",

        "document.delete",
        "document.delete_any",
    ],
}

async def seed():
    async with AsyncSessionLocal() as db:

        # --- permissions ---
        perm_map = {}

        for code in PERMISSIONS:
            result = await db.execute(
                select(Permission).where(Permission.code == code)
            )
            perm = result.scalar_one_or_none()

            if not perm:
                perm = Permission(code=code)
                db.add(perm)
                await db.flush()

            perm_map[code] = perm

        # --- roles ---
        for role_code, perms in ROLES.items():
            result = await db.execute(
                select(Role).where(Role.code == role_code)
            )
            role = result.scalar_one_or_none()

            if not role:
                role = Role(code=role_code)
                db.add(role)
                await db.flush()

            # 🔥 синхронизация (важно)
            result = await db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
            existing_perms = {
                rp.permission_id for rp in result.scalars().all()
            }

            for code in perms:
                perm = perm_map[code]

                if perm.id not in existing_perms:
                    db.add(RolePermission(
                        role_id=role.id,
                        permission_id=perm.id
                    ))

        await db.commit()