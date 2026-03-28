# app/services/document_service.py
from datetime import datetime
from app.models.document import DocumentStatus
from app.models.document_history import DocumentHistory
from app.models.document import Document
from app.models.document_watcher import DocumentWatcher
from app.models.notification import Notification
from app.websocket_manager import manager
from sqlalchemy import select


class DocumentService:

    @staticmethod
    async def update_document(db, doc, data, user):
        updates = data.model_dump(exclude_unset=True)

        # Сохраняем предыдущие значения для возможных уведомлений
        old_executor_id = doc.executor_id
        old_status = doc.status

        for field, new_value in updates.items():
            old_value = getattr(doc, field)

            if old_value == new_value:
                continue

            old_val = old_value.value if hasattr(old_value, "value") else old_value
            new_val = new_value.value if hasattr(new_value, "value") else new_value

            history = DocumentHistory(
                document_id=doc.id,
                changed_by=user.id,
                field=field,
                old_value=str(old_val),
                new_value=str(new_val),
            )
            setattr(doc, field, new_value)
            db.add(history)

        doc.updated_at = datetime.utcnow()

        if "status" in updates and updates["status"] == DocumentStatus.DONE:
            doc.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(doc)

        # --- Уведомления об изменениях ---
        participants = set()
        participants.add(doc.author_id)
        if doc.executor_id:
            participants.add(doc.executor_id)
        # добавим наблюдателей
        watchers_res = await db.execute(
            select(DocumentWatcher.user_id).where(DocumentWatcher.document_id == doc.id)
        )
        for watcher_id in watchers_res.scalars().all():
            participants.add(watcher_id)

        # Уведомление о смене исполнителя
        if "executor_id" in updates and old_executor_id != doc.executor_id:
            for uid in participants:
                if uid != user.id:
                    notif = Notification(
                        user_id=uid,
                        type="assign",
                        entity_id=doc.id,
                        is_read=False
                    )
                    db.add(notif)
                    await manager.send_to_user(str(uid), {
                        "type": "notification",
                        "data": {
                            "type": "assign",
                            "document_id": str(doc.id),
                            "new_executor": doc.executor.full_name if doc.executor else None,
                            "changed_by": user.full_name
                        }
                    })

        # Уведомление о смене статуса
        if "status" in updates and old_status != doc.status:
            for uid in participants:
                if uid != user.id:
                    notif = Notification(
                        user_id=uid,
                        type="status_change",
                        entity_id=doc.id,
                        is_read=False
                    )
                    db.add(notif)
                    await manager.send_to_user(str(uid), {
                        "type": "notification",
                        "data": {
                            "type": "status_change",
                            "document_id": str(doc.id),
                            "new_status": doc.status.value,
                            "changed_by": user.full_name
                        }
                    })

        # Уведомление о смене дедлайна
        if "deadline" in updates:
            for uid in participants:
                if uid != user.id:
                    notif = Notification(
                        user_id=uid,
                        type="deadline_change",
                        entity_id=doc.id,
                        is_read=False
                    )
                    db.add(notif)
                    await manager.send_to_user(str(uid), {
                        "type": "notification",
                        "data": {
                            "type": "deadline_change",
                            "document_id": str(doc.id),
                            "new_deadline": doc.deadline.isoformat(),
                            "changed_by": user.full_name
                        }
                    })

        await db.commit()
        return doc

    @staticmethod
    async def create_document(db, data, author_id):
        doc = Document(
            title=data.title,
            description=data.description,
            executor_id=data.executor_id,
            deadline=data.deadline,
            file_name=data.file_name,
            file_path=data.file_path,
            author_id=author_id,
        )

        db.add(doc)
        await db.flush()

        history = DocumentHistory(
            document_id=doc.id,
            changed_by=author_id,
            field="created",
            old_value="",
            new_value="created",
        )
        db.add(history)

        await db.commit()
        await db.refresh(doc)

        # Уведомление автору (не нужно) и исполнителю, если он есть
        if doc.executor_id:
            notif = Notification(
                user_id=doc.executor_id,
                type="new_document",
                entity_id=doc.id,
                is_read=False
            )
            db.add(notif)
            await manager.send_to_user(str(doc.executor_id), {
                "type": "notification",
                "data": {
                    "type": "new_document",
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "author": doc.author.full_name
                }
            })

        await db.commit()
        return doc