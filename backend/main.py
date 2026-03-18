from decimal import Decimal
from typing import Union

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session
import asyncio

import DB_models
import models
from database import engine, get_db

DB_models.Base.metadata.create_all(bind=engine)
app = FastAPI()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket_: WebSocket):
        await websocket_.accept()
        self.active_connections.append(websocket_)

    async def disconnect(self, websocket_: WebSocket):
        self.active_connections.remove(websocket_)

    async def send_message(self, websocket_: WebSocket, message: str):
        await websocket_.send_text(message)

    async def broadcast(self, message: str):
        tasks = [connection.send_text(message) for connection in self.active_connections]
        await asyncio.gather(*tasks)

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket_: WebSocket, client_id: int):
    await manager.connect(websocket_)

    try:
        while True:
            data = await websocket_.receive_text()
            print(data)
            await manager.send_message(websocket_, f"You sent: {data}")
            await manager.broadcast(f"{client_id} sent: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket_)