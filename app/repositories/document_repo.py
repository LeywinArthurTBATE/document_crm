from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
from datetime import date

from app.models.document import Document, DocumentStatus


class DocumentRepository:

    @staticmethod
    async def get_list(
        db: AsyncSession,
        user,
        status: Optional[str] = None,
        executor_id: Optional[UUID] = None,
        search: Optional[str] = None,
        deadline_from: Optional[date] = None,
        deadline_to: Optional[date] = None,
        is_overdue: Optional[bool] = None,
        limit: int = 50, offset: int = 0
    ):
        query = select(Document).where(Document.is_deleted == False)

        # 🔒 ограничение доступа (если не админ)
        if user.role.code != "ADMIN":
            query = query.where(
                (Document.author_id == user.id) |
                (Document.executor_id == user.id)
            )

        filters = []

        if status:
            filters.append(Document.status == DocumentStatus(status))
        if executor_id:
            filters.append(Document.executor_id == executor_id)

        if search:
            filters.append(Document.title.ilike(f"%{search}%"))

        if deadline_from:
            filters.append(Document.deadline >= deadline_from)

        if deadline_to:
            filters.append(Document.deadline <= deadline_to)

        if is_overdue is not None:
            filters.append(Document.is_overdue == is_overdue)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Document.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()