# app/models/document_watcher.py
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column
from app.models.base import Base

class DocumentWatcher(Base):
    __tablename__ = "document_watchers"

    document_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        primary_key=True,
    )

    user_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
    )

    created_at = mapped_column(DateTime, default=datetime.utcnow)