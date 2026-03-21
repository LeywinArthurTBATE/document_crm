from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional
from uuid import UUID
from app.models.document import DocumentStatus


class DocumentCreate(BaseModel):
    title: str
    description: Optional[str]
    executor_id: Optional[UUID]
    deadline: date

    file_name: str
    file_path: str


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    status: str
    deadline: date
    is_overdue: bool

    description: str | None
    file_name: str

    author_id: UUID
    executor_id: Optional[UUID]

    @field_validator("status", mode="before")
    def convert_status(cls, v):
        return v.value if hasattr(v, "value") else v

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    id: UUID
    title: str
    status: str
    deadline: date
    executor_id: Optional[UUID]
    executor_name: str | None  # ← новое поле
    file_name: str | None
    is_overdue: bool
    author_id: UUID
    author_name: str  # 👈 добавить
    description: str | None
    @field_validator("status", mode="before")
    def convert_status(cls, v):
        return v.value if hasattr(v, "value") else v

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    executor_id: Optional[UUID] = None
    deadline: Optional[date] = None
    status: Optional[DocumentStatus] = None