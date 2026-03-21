import uuid
from datetime import datetime, date

from sqlalchemy import String, ForeignKey, DateTime, Text, Boolean, Date, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
import enum


class DocumentStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ON_REVIEW = "ON_REVIEW"
    REJECTED = "REJECTED"
    REVISION = "REVISION"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    DONE = "DONE"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String, nullable=False)

    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        default=DocumentStatus.NEW,
        nullable=False,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    executor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    deadline: Mapped[date] = mapped_column(Date, nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    author = relationship("User", foreign_keys=[author_id])
    executor = relationship("User", foreign_keys=[executor_id])