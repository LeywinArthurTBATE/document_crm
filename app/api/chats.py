# app/api/chats.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.websockets import WebSocketDisconnect

from app.core.database import get_db
from app.core.documents_access import can_access_document, get_doc_or_403
from app.core.security import decode_token
from app.dependencies.auth import get_current_user
from app.models import DocumentHistory, Document, DocumentWatcher, Notification, User
from app.models.document_message import DocumentMessage

from app.websocket_manager import manager

router = APIRouter(prefix="/chats", tags=["documents"])


@router.get("")
async def get_user_chats(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    # --- базовый фильтр документов ---
    doc_query = select(
        Document.id,
        Document.title
    ).where(
        Document.is_deleted.is_(False)
    )

    if user.role.code != "ADMIN":
        doc_query = doc_query.where(
            or_(
                Document.author_id == user.id,
                Document.executor_id == user.id,
                Document.id.in_(
                    select(DocumentWatcher.document_id)
                    .where(DocumentWatcher.user_id == user.id)
                )
            )
        )

    # --- подзапрос: последнее сообщение ---
    subq = (
        select(
            DocumentMessage.document_id,
            func.max(DocumentMessage.created_at).label("last_time")
        )
        .group_by(DocumentMessage.document_id)
        .subquery()
    )

    # --- основной запрос ---
    query = (
        select(
            Document.id,
            Document.title,
            DocumentMessage.text,
            DocumentMessage.created_at
        )
        .select_from(Document)
        .outerjoin(subq, subq.c.document_id == Document.id)
        .outerjoin(
            DocumentMessage,
            and_(
                DocumentMessage.document_id == Document.id,
                DocumentMessage.created_at == subq.c.last_time
            )
        )
        .where(Document.id.in_(doc_query.with_only_columns(Document.id)))
        .order_by(DocumentMessage.created_at.desc().nullslast())
    )

    result = await db.execute(query)

    rows = result.all()

    return [
        {
            "document_id": doc_id,
            "title": title,
            "last_message": text,
            "last_time": created_at
        }
        for doc_id, title, text, created_at in rows
    ]


@router.post("/{doc_id}/messages")
async def send_message(
    doc_id: UUID,
    text: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    # сообщение
    msg = DocumentMessage(
        document_id=doc_id,
        author_id=user.id,
        text=text
    )
    db.add(msg)

    # участники
    watchers_res = await db.execute(
        select(DocumentWatcher.user_id)
        .where(DocumentWatcher.document_id == doc_id)
    )
    watchers = set(watchers_res.scalars().all())

    participants = set(filter(None, [
        doc.author_id,
        doc.executor_id,
        *watchers
    ]))

    # уведомления
    for uid in participants:
        if uid == user.id:
            continue

        db.add(Notification(
            user_id=uid,
            type="message",
            entity_id=doc_id,
            is_read=False
        ))

        await manager.send_to_user(str(uid), {
            "type": "notification",
            "data": {
                "type": "message",
                "document_id": str(doc_id),
                "author_name": user.full_name,
                "text": text[:50]
            }
        })

    await db.commit()

    # рассылка сообщения
    await manager.send_to_document(str(doc_id), {
        "type": "message",
        "data": {
            "id": str(msg.id),
            "author_id": str(user.id),
            "author_name": user.full_name,
            "text": text,
            "created_at": msg.created_at.isoformat()
        }
    })

    return {"status": "ok"}

@router.websocket("/ws/{doc_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return

        result = await db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    doc, access = await can_access_document(db, user, doc_id)
    if not doc:
        await websocket.close(code=1003)
        return

    await manager.connect(websocket, str(doc_id), str(user.id))

    try:
        while True:
            data = await websocket.receive_json()
            text = data.get("text")
            if not text:
                continue

            msg = DocumentMessage(
                document_id=doc_id,
                author_id=user.id,
                text=text
            )
            db.add(msg)

            # участники (единая логика)
            watchers_res = await db.execute(
                select(DocumentWatcher.user_id)
                .where(DocumentWatcher.document_id == doc_id)
            )
            watchers = set(watchers_res.scalars().all())

            participants = set(filter(None, [
                doc.author_id,
                doc.executor_id,
                *watchers
            ]))

            for uid in participants:
                if uid == user.id:
                    continue

                db.add(Notification(
                    user_id=uid,
                    type="message",
                    entity_id=doc_id,
                    is_read=False
                ))

                await manager.send_to_user(str(uid), {
                    "type": "notification",
                    "event": "message",
                    "data": {
                        "document_id": str(doc_id),
                        "document_title": doc.title,
                        "url": f"/documents/{doc_id}/view",

                        "actor_id": str(user.id),
                        "actor_name": user.full_name,

                        "text": text
                    },
                    "meta": {
                        "created_at": msg.created_at.isoformat(),
                        "id": str(msg.id)
                    }
                })

            await db.commit()

            await manager.send_to_document(str(doc_id), {
                "type": "message",
                "data": {
                    "id": str(msg.id),
                    "author_id": str(user.id),
                    "author_name": user.full_name,
                    "text": text,
                    "created_at": msg.created_at.isoformat()
                }
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, str(doc_id), str(user.id))

@router.get("/{doc_id}/messages")
async def get_messages(
    doc_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    result = await db.execute(
        select(DocumentMessage)
        .where(DocumentMessage.document_id == doc_id)
        .order_by(DocumentMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    author_ids = {m.author_id for m in messages}

    users_map = {}
    if author_ids:
        res = await db.execute(select(User).where(User.id.in_(author_ids)))
        users_map = {u.id: u.full_name for u in res.scalars().all()}

    return [
        {
            "id": m.id,
            "author_id": m.author_id,
            "author_name": users_map.get(m.author_id, "Неизвестный"),
            "text": m.text,
            "created_at": m.created_at.isoformat()
        }
        for m in reversed(messages)
    ]