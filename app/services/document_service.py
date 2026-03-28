from datetime import datetime
from sqlalchemy import select

from app.models.document import DocumentStatus
from app.models.document_history import DocumentHistory
from app.models.document import Document
from app.models.document_watcher import DocumentWatcher
from app.models.notification import Notification
from app.models.user import User
from app.websocket_manager import manager


class DocumentService:

    @staticmethod
    async def update_document(db, doc, data, user):
        updates = data.model_dump(exclude_unset=True)

        old_executor_id = doc.executor_id
        old_status = doc.status

        # -------------------- UPDATE + HISTORY --------------------
        for field, new_value in updates.items():
            old_value = getattr(doc, field)

            if old_value == new_value:
                continue

            old_val = old_value.value if hasattr(old_value, "value") else old_value
            new_val = new_value.value if hasattr(new_value, "value") else new_value

            db.add(DocumentHistory(
                document_id=doc.id,
                changed_by=user.id,
                field=field,
                old_value=str(old_val),
                new_value=str(new_val),
            ))

            setattr(doc, field, new_value)

        doc.updated_at = datetime.utcnow()

        if updates.get("status") == DocumentStatus.DONE:
            doc.completed_at = datetime.utcnow()

        await db.flush()  # важно: не commit, чтобы не терять контекст

        # -------------------- PARTICIPANTS --------------------
        participants = {doc.author_id}

        if doc.executor_id:
            participants.add(doc.executor_id)

        watchers_res = await db.execute(
            select(DocumentWatcher.user_id)
            .where(DocumentWatcher.document_id == doc.id)
        )
        participants.update(watchers_res.scalars().all())

        # -------------------- LOAD USERS (ОДИН ЗАПРОС) --------------------
        user_ids_to_load = set(participants)
        user_ids_to_load.add(user.id)

        res = await db.execute(
            select(User.id, User.full_name)
            .where(User.id.in_(user_ids_to_load))
        )
        users_map = {u.id: u.full_name for u in res.all()}

        executor_name = users_map.get(doc.executor_id)

        # -------------------- HELPER --------------------
        async def notify(uid, event, notif_type):
            db.add(Notification(
                user_id=uid,
                type=notif_type,
                entity_id=doc.id,
                is_read=False
            ))

            await manager.send_to_user(str(uid), {
                "type": "notification",
                "event": event,
                "data": {
                    "document_id": str(doc.id),
                    "document_title": doc.title,
                    "url": f"/documents/{doc.id}/view",
                    "actor_id": str(user.id),
                    "actor_name": users_map.get(user.id),
                    "extra": {
                        "new_executor": executor_name
                    }
                },
                "meta": {
                    "created_at": datetime.utcnow().isoformat()
                }
            })

        # -------------------- EVENTS --------------------
        if "executor_id" in updates and old_executor_id != doc.executor_id:
            for uid in participants:
                if uid != user.id:
                    await notify(uid, "assign", "assign")

        if "status" in updates and old_status != doc.status:
            for uid in participants:
                if uid != user.id:
                    await notify(uid, "status_change", "status_change")

        if "deadline" in updates:
            for uid in participants:
                if uid != user.id:
                    await notify(uid, "deadline_change", "deadline_change")

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

        db.add(DocumentHistory(
            document_id=doc.id,
            changed_by=author_id,
            field="created",
            old_value="",
            new_value="created",
        ))

        # заранее грузим нужных пользователей
        user_ids = {author_id}
        if doc.executor_id:
            user_ids.add(doc.executor_id)

        res = await db.execute(
            select(User.id, User.full_name)
            .where(User.id.in_(user_ids))
        )
        users_map = {u.id: u.full_name for u in res.all()}

        if doc.executor_id:
            db.add(Notification(
                user_id=doc.executor_id,
                type="new_document",
                entity_id=doc.id,
                is_read=False
            ))

            await manager.send_to_user(str(doc.executor_id), {
                "type": "notification",
                "event": "new_document",
                "data": {
                    "document_id": str(doc.id),
                    "document_title": doc.title,
                    "url": f"/documents/{doc.id}/view",
                    "actor_name": users_map.get(author_id),
                },
                "meta": {
                    "created_at": datetime.utcnow().isoformat()
                }
            })

        await db.commit()
        return doc