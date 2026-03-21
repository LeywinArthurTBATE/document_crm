from datetime import datetime
from app.models.document import DocumentStatus
from app.models.document_history import DocumentHistory
from app.models.document import Document

class DocumentService:

    @staticmethod
    async def update_document(db, doc, data, user):

        updates = data.model_dump(exclude_unset=True)

        for field, new_value in updates.items():
            old_value = getattr(doc, field)

            if old_value == new_value:
                continue

            # если enum → сохраняем value
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
            doc.updated_at = datetime.utcnow()
            db.add(history)

        # ✅ корректная логика completed_at
        if "status" in updates and updates["status"] == DocumentStatus.DONE:
            doc.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(doc)

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
        await db.flush()  # чтобы получить doc.id

        # история создания
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

        return doc