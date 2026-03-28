# app/workers/overdue_worker.py
from datetime import datetime, date
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentStatus
from app.models.document_watcher import DocumentWatcher
from app.models.notification import Notification
from app.websocket_manager import manager


async def process_overdue_documents(db: AsyncSession):
    today = datetime.utcnow().date()

    # Находим документы, которые стали просроченными
    stmt_new = (
        select(Document)
        .where(
            Document.deadline < today,
            Document.status != DocumentStatus.DONE,
            Document.is_overdue.is_(False),
            Document.is_deleted.is_(False)
        )
    )
    result = await db.execute(stmt_new)
    new_overdue_docs = result.scalars().all()

    # Обновляем флаг для них
    if new_overdue_docs:
        await db.execute(
            update(Document)
            .where(Document.id.in_([doc.id for doc in new_overdue_docs]))
            .values(is_overdue=True)
        )

        # Для каждого документа создаём уведомления
        for doc in new_overdue_docs:
            participants = set()
            participants.add(doc.author_id)
            if doc.executor_id:
                participants.add(doc.executor_id)
            # добавляем watchers
            watchers_res = await db.execute(
                select(DocumentWatcher.user_id).where(DocumentWatcher.document_id == doc.id)
            )
            for watcher_id in watchers_res.scalars().all():
                participants.add(watcher_id)

            for uid in participants:
                notification = Notification(
                    user_id=uid,
                    type="overdue",
                    entity_id=doc.id,
                    is_read=False
                )
                db.add(notification)

                # Отправляем через вебсокет
                await manager.send_to_user(str(uid), {
                    "type": "notification",
                    "data": {
                        "type": "overdue",
                        "document_id": str(doc.id),
                        "title": doc.title,
                        "deadline": doc.deadline.isoformat()
                    }
                })

    # Снимаем флаг с документов, которые больше не просрочены
    await db.execute(
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

    await db.commit()
    print(f"[overdue_worker] new overdue: {len(new_overdue_docs)}")