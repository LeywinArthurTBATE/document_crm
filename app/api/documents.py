from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    UploadFile, File, Form
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.repositories.permissions import require_permission
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse, DocumentUpdate
)
from app.services.document_service import DocumentService
from app.repositories.document_repo import DocumentRepository
from app.utils.file_storage import save_file

router = APIRouter(prefix="/documents", tags=["documents"])


# -------------------- LIST --------------------

@router.get("", response_model=List[DocumentListResponse])
async def get_documents(
    status: Optional[str] = Query(None),
    executor_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    deadline_from: Optional[date] = Query(None),
    deadline_to: Optional[date] = Query(None),
    is_overdue: Optional[bool] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.read")
    return await DocumentRepository.get_list(
        db=db,
        user=user,
        status=status,
        executor_id=executor_id,
        search=search,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        is_overdue=is_overdue,
        limit=limit,
        offset=offset,
    )


# -------------------- CREATE --------------------

@router.post("", response_model=DocumentResponse)
async def create_document(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    executor_id: Optional[UUID] = Form(None),
    deadline: date = Form(...),
    file: UploadFile = File(...),

    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.create")
    # 🔒 Валидация файла
    ext = file.filename.split(".")[-1].lower()
    allowed = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "png"}

    if ext not in allowed:
        raise HTTPException(400, "Invalid file type")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large")

    file.file.seek(0)

    # 💾 сохраняем файл
    file_name, file_path = await save_file(file)

    # создаем документ сразу с файлом
    doc_data = DocumentCreate(
        title=title,
        description=description,
        executor_id=executor_id,
        deadline=deadline,
        file_name=file_name,
        file_path=file_path,
    )

    return await DocumentService.create_document(
        db=db,
        data=doc_data,
        author_id=user.id,
    )


# -------------------- GET ONE --------------------

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    # 🔒 проверка доступа
    await require_permission(db, user, "document.read")
    if user.id not in [doc.author_id, doc.executor_id]:
        raise HTTPException(403, "Access denied")

    return doc


# -------------------- DOWNLOAD --------------------

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.read")

    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    if user.id not in [doc.author_id, doc.executor_id]:
        raise HTTPException(403, "Access denied")

    return FileResponse(doc.file_path, filename=doc.file_name)

# -------------------- DELETE --------------------

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.delete")

    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    # ownership OR admin permission
    is_owner = doc.author_id == user.id

    if not is_owner:
        # если не владелец — нужен отдельный permission
        await require_permission(db, user, "document.delete_any")

    doc.is_deleted = True
    await db.commit()

    return {"status": "deleted"}


# -------------------- PATCH --------------------

@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    # ownership
    if user.id not in [doc.author_id, doc.executor_id]:
        raise HTTPException(403, "Access denied")

    # granular permissions
    if data.deadline:
        await require_permission(db, user, "document.edit_deadline")

    if data.executor_id:
        await require_permission(db, user, "document.assign")

    if data.status:
        await require_permission(db, user, "document.change_status")

    updated = await DocumentService.update_document(db, doc, data, user)

    return updated

@router.get("/{doc_id}/history")
async def get_document_history(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    await require_permission(db, user, "document.read")

    result = await db.execute(
        select(DocumentHistory)
        .where(DocumentHistory.document_id == doc_id)
        .order_by(DocumentHistory.created_at.desc())
    )

    return result.scalars().all()