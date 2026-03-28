from fastapi import HTTPException
from sqlalchemy import select


async def can_access_document(db, user, doc_id):
    from app.models import DocumentWatcher, Document

    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.is_deleted.is_(False)
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return None, None

    if user.role.code == "ADMIN":
        return doc, "admin"

    if user.id in [doc.author_id, doc.executor_id]:
        return doc, "owner"

    res = await db.execute(
        select(DocumentWatcher).where(
            DocumentWatcher.document_id == doc_id,
            DocumentWatcher.user_id == user.id
        )
    )
    if res.scalar_one_or_none():
        return doc, "watcher"

    return None, None

async def get_doc_or_403(db, user, doc_id):
    doc, access = await can_access_document(db, user, doc_id)
    if not doc:
        raise HTTPException(403, "Access denied")
    return doc, access
