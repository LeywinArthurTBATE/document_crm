from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    UploadFile, File, Form
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import DocumentHistory
from app.repositories.permissions import require_permission
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse, DocumentUpdate
)
from app.services.document_service import DocumentService
from app.repositories.document_repo import DocumentRepository
from app.utils.file_storage import save_file, save_file_stream

router = APIRouter(prefix="/documents", tags=["documents"])

async def check_owner_or_permission(db, user, doc, perm_own, perm_any):
    if user.id in [doc.author_id, doc.executor_id]:
        await require_permission(db, user, perm_own)
    else:
        await require_permission(db, user, perm_any)
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

    # 🔒 проверка расширения
    ext = file.filename.split(".")[-1].lower()
    allowed = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "png", "webp"}

    if ext not in allowed:
        raise HTTPException(400, "Invalid file type")

    # 💾 сохраняем файл потоково
    try:
        file_name, file_path = await save_file_stream(file)
    except ValueError:
        raise HTTPException(400, "File too large")

    # создаем документ
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

    if user.id in [doc.author_id, doc.executor_id]:
        await require_permission(db, user, "document.read")
    else:
        await require_permission(db, user, "document.read_any")

    return doc


# -------------------- DOWNLOAD --------------------

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    await check_owner_or_permission(
        db, user, doc,
        "document.delete",
        "document.delete_any"
    )

    doc.is_deleted = True
    await db.commit()

    return {"status": "deleted"}
# -------------------- DELETE --------------------

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):

    doc = await DocumentRepository.get_by_id(db, doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    is_owner = doc.author_id == user.id

    if is_owner:
        await require_permission(db, user, "document.delete")
    else:
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

    # --- базовый доступ ---
    await check_owner_or_permission(
        db, user, doc,
        "document.edit",
        "document.edit_any"
    )

    # --- granular ---
    if data.deadline:
        await require_permission(db, user, "document.edit_deadline")

    if data.executor_id:
        if user.id in [doc.author_id, doc.executor_id]:
            await require_permission(db, user, "document.assign")
        else:
            await require_permission(db, user, "document.assign_any")

    if data.status:
        if user.id in [doc.author_id, doc.executor_id]:
            await require_permission(db, user, "document.change_status")
        else:
            await require_permission(db, user, "document.change_status_any")

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
        raise HTTPException(404)

    if user.id in [doc.author_id, doc.executor_id]:
        await require_permission(db, user, "document.read")
    else:
        await require_permission(db, user, "document.read_any")

    result = await db.execute(
        select(DocumentHistory)
        .where(DocumentHistory.document_id == doc_id)
        .order_by(DocumentHistory.created_at.desc())
    )

    history = result.scalars().all()

    # 🔥 собираем список user_id
    user_ids = set()
    for h in history:
        if h.field == "executor_id":
            if h.old_value:
                user_ids.add(h.old_value)
            if h.new_value:
                user_ids.add(h.new_value)

    users_map = {}

    if user_ids:
        from app.models.user import User
        res = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = res.scalars().all()
        users_map = {str(u.id): u.full_name for u in users}

    # 🔥 преобразуем
    response = []

    for h in history:
        old_val = h.old_value
        new_val = h.new_value

        if h.field == "executor_id":
            old_val = users_map.get(old_val, "—")
            new_val = users_map.get(new_val, "—")

        response.append({
            "field": h.field,
            "old_value": old_val,
            "new_value": new_val,
            "created_at": h.created_at,
            "changed_by": str(h.changed_by),
        })

    return response