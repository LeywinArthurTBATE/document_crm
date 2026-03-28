# app/websocket_manager.py
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # doc_id -> websockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}    # user_id -> websockets

    async def connect(self, websocket: WebSocket, doc_id: str, user_id: str):
        # по документу
        if doc_id not in self.active_connections:
            self.active_connections[doc_id] = set()
        self.active_connections[doc_id].add(websocket)
        # по пользователю
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, doc_id: str, user_id: str):
        if doc_id in self.active_connections:
            self.active_connections[doc_id].discard(websocket)
            if not self.active_connections[doc_id]:
                del self.active_connections[doc_id]
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_document(self, doc_id: str, message: dict):
        """Отправить сообщение всем, кто следит за документом."""
        if doc_id in self.active_connections:
            for connection in self.active_connections[doc_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

    async def send_to_user(self, user_id: str, message: dict):
        """Отправить сообщение конкретному пользователю."""
        if user_id in self.user_connections:
            for ws in self.user_connections[user_id]:
                try:
                    await ws.send_json(message)
                except:
                    pass

manager = ConnectionManager()