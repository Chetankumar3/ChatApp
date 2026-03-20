from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from database import AsyncSessionLocal, engine, get_db
import DB_models
from connection_manager import manager
import asyncio

router = APIRouter()

@router.websocket("/ws/{Username}")
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
            data = await websocket_.receive_json()

            Group = []
            async with AsyncSessionLocal() as db:
                if data["Type"]==0:
                    DBMessage = DB_models.Message(
                        FromId=data["FromId"],
                        ToId=data["ToId"],
                        Body=data["Body"],
                        SentAt=data["SentAt"]
                    )
                    db.add(DBMessage)
                    await db.commit()
                elif data["Type"]==1:
                    DBGroupMessage = DB_models.Message(
                        FromId=data["FromId"],
                        ToId=data["ToId"],
                        Body=data["Body"],
                        SentAt=data["SentAt"]
                    )
                    db.add(DBGroupMessage)
                    await db.flush()
                    await db.refresh(DBGroupMessage)

                    Group = await db.scalars(
                        select(DB_models.MapTable.UserId)
                        .where(DB_models.MapTable.GroupId == data["ToId"])
                    )
                    Group = Group.all()

                    DBMessageReceipt = [
                        DB_models.MessageReceipt(
                            GroupMessageId=DBGroupMessage.Id,
                            UserId=UserId
                        ) for UserId in Group]

                    db.add_all(DBMessageReceipt)

                    DBCurrentUserReceipt = DB_models.MessageReceipt(
                        GroupMessageId=DBGroupMessage.Id,
                        UserId=data["FromId"],
                        ReceivedAt=data["SentAt"]
                    )
                    db.merge(DBCurrentUserReceipt)
                    await db.commit()

            if data["Type"]==0:
                await manager.send_message(data, data["ToId"])
            elif data["Type"]==1:
                Tasks = [manager.send_message(data, To_) for To_ in Group]
                await asyncio.gather(*Tasks)

    except WebSocketDisconnect:
        await manager.disconnect(websocket_, UserId)
