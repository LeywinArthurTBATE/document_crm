import json
from typing import Dict, Set, Tuple
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.ws_meta: Dict[WebSocket, Tuple[str, str]] = {}  # 🔥 ключ

    async def connect(self, websocket: WebSocket, doc_id: str, user_id: str):
        # doc
        self.active_connections.setdefault(doc_id, set()).add(websocket)

        # user
        self.user_connections.setdefault(user_id, set()).add(websocket)

        # meta
        self.ws_meta[websocket] = (doc_id, user_id)

    def disconnect(self, websocket: WebSocket):
        meta = self.ws_meta.pop(websocket, None)
        if not meta:
            return

        doc_id, user_id = meta

        # doc cleanup
        if doc_id in self.active_connections:
            self.active_connections[doc_id].discard(websocket)
            if not self.active_connections[doc_id]:
                del self.active_connections[doc_id]

        # user cleanup
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_document(self, doc_id: str, message: dict):
        if doc_id not in self.active_connections:
            return

        dead = []

        for ws in list(self.active_connections[doc_id]):
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id not in self.user_connections:
            return

        dead = []

        for ws in list(self.user_connections[user_id]):
            try:
                text = json.dumps(message, ensure_ascii=False)
                print(text)
                await ws.send_text(
                    text
                )
            except:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()