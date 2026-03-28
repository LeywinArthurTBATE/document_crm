import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column
from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = mapped_column(UUID, ForeignKey("users.id"))
    type = mapped_column(String)  # message / overdue

    entity_id = mapped_column(UUID)  # document_id

    is_read = mapped_column(Boolean, default=False)

    created_at = mapped_column(DateTime, default=datetime.utcnow)