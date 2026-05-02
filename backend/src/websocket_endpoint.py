from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from database import AsyncSessionLocal
import DB_models
from .connection_manager import manager
from .login import get_current_websocket_user
import asyncio
from datetime import datetime

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket_: WebSocket,
    user_id: int
):
    await manager.connect(websocket_, user_id)

    try:
        while True:
            data = await websocket_.receive_json()

            group_users = []
            async with AsyncSessionLocal() as db:
                if data["type"] == "direct_message":
                    DBMessage = DB_models.message(
                        fromId=data["fromId"],
                        toId=data["toId"],
                        body=data["body"],
                        sentAt=datetime.fromisoformat(
                            data["sentAt"].replace("Z", "+00:00")
                        ),
                    )
                    db.add(DBMessage)
                    await db.commit()
                elif data["type"] == "group_message":
                    DBGroupMessage = DB_models.groupMessage(
                        fromId=data["fromId"],
                        toId=data["toId"],
                        body=data["body"],
                        sentAt=datetime.fromisoformat(
                            data["sentAt"].replace("Z", "+00:00")
                        ),
                    )
                    db.add(DBGroupMessage)
                    await db.flush()
                    await db.refresh(DBGroupMessage)

                    group_users = await db.scalars(
                        select(DB_models.mapTable.userId).where(
                            DB_models.mapTable.groupId == data["toId"]
                        )
                    )
                    group_users = group_users.all()

                    message_receipts = [
                        DB_models.messageReceipt(
                            groupMessageId=DBGroupMessage.id, userId=u
                        )
                        for u in group_users
                    ]

                    db.add_all(message_receipts)

                    current_user_receipt = DB_models.messageReceipt(
                        groupMessageId=DBGroupMessage.id,
                        userId=data["fromId"],
                        receivedAt=datetime.fromisoformat(
                            data["sentAt"].replace("Z", "+00:00")
                        ),
                    )
                    db.merge(current_user_receipt)
                    await db.commit()

            if data["type"] == "direct_message":
                await manager.send_message(data, data["toId"])
            elif data["type"] == "group_message":
                tasks = [manager.send_message(data, to_) for to_ in group_users]
                await asyncio.gather(*tasks)

    except HTTPException:
        raise
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
