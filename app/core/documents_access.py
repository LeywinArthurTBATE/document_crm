from sqlalchemy import select

async def can_access_document(db, user, doc_id):
    from app.models import DocumentWatcher, Document

    result = await db.execute(
        select(Document)
        .where(
            Document.id == doc_id,
            Document.is_deleted.is_(False)
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return None

    if user.role.code == "ADMIN":
        return doc

    # автор / исполнитель
    if user.id in [doc.author_id, doc.executor_id]:
        return doc

    # наблюдатель
    res = await db.execute(
        select(DocumentWatcher).where(
            DocumentWatcher.document_id == doc_id,
            DocumentWatcher.user_id == user.id
        )
    )
    if res.scalar_one_or_none():
        return doc

    return None
