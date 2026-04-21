import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Boolean, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column
from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID, ForeignKey("users.id"))
    type = mapped_column(String)           # message, status_change, assign, deadline_change, overdue, new_document
    entity_id = mapped_column(UUID)        # document_id

    # Новые поля для отображения контекста
    document_title = mapped_column(String, nullable=True)
    actor_name = mapped_column(String, nullable=True)
    message_text = mapped_column(String, nullable=True)   # для сообщений чата или дополнительного текста
    extra_data = mapped_column(JSON, nullable=True)       # например, { "new_status": "DONE", "old_deadline": "2025-04-01" }

    is_read = mapped_column(Boolean, default=False)
    created_at = mapped_column(DateTime, default=datetime.utcnow)