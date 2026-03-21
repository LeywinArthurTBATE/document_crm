from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
from datetime import date

from app.models import User
from app.models.document import Document, DocumentStatus


class DocumentRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, doc_id: UUID) -> Optional[Document]:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.is_deleted.is_(False)
            )
        )
        return result.scalar_one_or_none()

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
        query = (
            select(Document, User)
            .outerjoin(User, Document.executor_id == User.id).where(Document.is_deleted == False)
        )

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
        rows = result.all()

        data = []
        for doc, executor in rows:
            data.append({
                "id": doc.id,
                "title": doc.title,
                "status": doc.status.value,
                "deadline": doc.deadline,
                "executor_id": doc.executor_id,
                "executor_name": executor.full_name if executor else None,
                "is_overdue": doc.is_overdue,
                "file_name": doc.file_name
            })

        return data