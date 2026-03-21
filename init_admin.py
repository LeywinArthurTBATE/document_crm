import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password

from app.models.user import User, UserRole


ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Admin"


async def create_admin():
    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        admin = result.scalar_one_or_none()

        if admin:
            print("✅ Админ уже существует:", admin.email)
            return

        new_admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),  # ✅ фикс
            full_name=ADMIN_NAME,                         # ✅ фикс
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(new_admin)
        await db.commit()

        print("🔥 Админ создан:")
        print(f"email: {ADMIN_EMAIL}")
        print(f"password: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(create_admin())