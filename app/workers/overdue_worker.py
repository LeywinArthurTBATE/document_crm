from datetime import datetime

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus


async def process_overdue_documents(db: AsyncSession):
    now = datetime.utcnow().date()

    # 🔴 ставим overdue = True
    stmt_overdue = (
        update(Document)
        .where(
            Document.deadline < now,
            Document.status != DocumentStatus.DONE,
            Document.is_deleted == False,
        )
        .values(is_overdue=True)
    )

    # 🟢 убираем overdue если исправили
    stmt_clear = (
        update(Document)
        .where(
            (Document.deadline >= now) | (Document.status == DocumentStatus.DONE),
            Document.is_overdue == True,
        )
        .values(is_overdue=False)
    )

    await db.execute(stmt_overdue)
    await db.execute(stmt_clear)

    await db.commit()