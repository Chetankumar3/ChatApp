from fastapi import WebSocket
import models

class connectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket_: WebSocket, userId: int):
        await websocket_.accept()
        self.active_connections[userId] = websocket_

    async def disconnect(self, userId: int):
        del self.active_connections[userId]

    async def send_message(self, data: models.message, toId: int):
        if toId in self.active_connections:
            await self.active_connections[toId].send_json(data)


manager = connectionManager()  