from datetime import datetime, date
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentStatus

async def process_overdue_documents(db: AsyncSession):
    today = datetime.utcnow().date()

    # 🔴 ставим overdue
    stmt = (
        update(Document)
        .where(
            Document.deadline < today,
            Document.status != DocumentStatus.DONE,
            Document.is_overdue.is_(False),
            Document.is_deleted.is_(False)
        )
        .values(is_overdue=True)
    )

    # 🟢 снимаем overdue
    stmt_clear = (
        update(Document)
        .where(
            Document.is_overdue.is_(True),
            Document.is_deleted.is_(False),
            (
                (Document.deadline >= today) |
                (Document.status == DocumentStatus.DONE)
            )
        )
        .values(is_overdue=False)
    )

    result1 = await db.execute(stmt)
    result2 = await db.execute(stmt_clear)

    await db.commit()

    print(f"[overdue_worker] set={result1.rowcount}, cleared={result2.rowcount}")