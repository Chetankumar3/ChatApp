from FastAPI import WebSocket
import app.models as models

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket_: WebSocket, UserId: int):
        await websocket_.accept()
        self.active_connections[UserId] = websocket_

    async def disconnect(self, UserId: int):
        del self.active_connections[UserId]

    async def send_message(self, data: models.Message, ToId: int):
        if ToId in self.active_connections:
            await self.active_connections[ToId].send_json(data)


manager = ConnectionManager()  