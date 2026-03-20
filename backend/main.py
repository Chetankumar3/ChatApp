import os
from decimal import Decimal
from typing import Union

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, exists, select, update, or_
from sqlalchemy.orm import Session
import asyncio
from google.oauth2 import id_token
from google.auth.transport import requests

from contextlib import asynccontextmanager
from database import AsyncSessionLocal, engine, get_db
import DB_models
from models import Message

WEBCLIENT_ID = os.getenv("WEBCLIENT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(DB_models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting up: Ensuring database tables exist...")
    await init_db()

    yield
    print("Shutting down gracefully...")
app = FastAPI(lifespan=lifespan)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket_: WebSocket, UserId: int):
        await websocket_.accept()
        self.active_connections[UserId] = websocket_

    async def disconnect(self, UserId: int):
        del self.active_connections[UserId]

    async def send_message(self, message: Message, ToId: int):
        if ToId in self.active_connections:
            await self.active_connections[ToId].send_json(message)

manager = ConnectionManager()

@app.post("/login")
async def login(token: str, db: Session = Depends(get_db)):
    try:
        IdInfo = id_token.verify_oauth2_token(token, requests.Request(), WEBCLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")

    try:
        userid = await db.scalar(
                        select(DB_models.OAuthTable.UserId)
                        .where(DB_models.OAuthTable.OAuthId==IdInfo["sub"])
                    )
    
        if not userid:
            user_ = DB_models.User(
                Name=IdInfo["name"],
                Email=IdInfo["email"],
                ProfilePictureUrl=IdInfo.get("picture")
            )

            db.add(user_)
            await db.flush()
            await db.refresh(user_)

            outh_ = DB_models.OAuthTable(
                UserId=user_.Id,
                OAuthId=IdInfo["sub"]
            )

            db.add(outh_)
            await db.commit()
            
            return {"UserId": user_.Id}

        return {"UserId": userid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/ws/{UserId}/get_all_messages")
async def get_all_messages(UserId: int, db: Session = Depends(get_db)):
    try:
        Messages = await db.scalars(
            select(DB_models.Message)
            .where(or_(DB_models.Message.FromId==UserId, DB_models.Message.ToId==UserId))
        )
        Messages = Messages.all()

        Groups = await db.scalars(
            select(DB_models.MapTable.GroupId)
            .where(DB_models.MapTable.UserId == UserId)
        )
        Groups = Groups.all()

        GroupMessages = await db.scalars(
            select(DB_models.GroupMessage)
            .where(DB_models.GroupMessage.GroupId.in_(Groups))
        )
        GroupMessages = GroupMessages.all()

        return {"Messages": Messages, "GroupMessages": GroupMessages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/change_username")
async def change_username(UserId: int, NewUsername: str, db: Session = Depends(get_db)):
    try:
        await db.execute(
            update(DB_models.User)
            .where(DB_models.User.Id == UserId)
            .values(Username=NewUsername)
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_all_users")
async def get_all_users(db: Session = Depends(get_db)):
    try:
        result = await db.scalars(select(DB_models.User.Id, DB_models.User.Username))
        return {"Users": result.mappings().all()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{Username}")
async def websocket_endpoint(websocket_: WebSocket, Username: str):
    UserId: 0
    async with AsyncSessionLocal() as db:
        UserId = await db.scalar(
            select(DB_models.User.Id)
            .where(DB_models.User.Username == Username)
        )

    if not UserId:
        websocket_.close(code=1008)

    await manager.connect(websocket_, UserId)

    try:
        while True:
            message = await websocket_.receive_json()

            async with AsyncSessionLocal() as db:
                if message["Type"]==0:
                    Message = DB_models.Message(
                        FromId=message["FromId"],
                        ToId=message["ToId"],
                        Message=message["Message"],
                        SentAt=message["SentAt"]
                    )
                    db.add(Message)
                    await db.commit()
                elif message["Type"]==1:
                    GroupMessage = DB_models.Message(
                        FromId=message["FromId"],
                        ToId=message["ToId"],
                        Message=message["Message"],
                        SentAt=message["SentAt"]
                    )
                    db.add(GroupMessage)
                    await db.commit()

            if message["Type"]==0:
                await manager.send_message(message, message["ToId"])

            elif message["Type"]==1:
                Group = await db.scalars(
                        select(DB_models.MapTable.UserId)
                        .where(DB_models.MapTable.GroupId == message["ToId"])
                    )
                Group = Group.all()

                Tasks = [manager.send_message(message, To_) for To_ in Group]
                await asyncio.gather(*Tasks)

    except WebSocketDisconnect:
        await manager.disconnect(websocket_, UserId)
'''
Left:
- Receive time updation
- Message deletion
- Group creation & deletion

For frontend: username change = websocket re-establish.
'''