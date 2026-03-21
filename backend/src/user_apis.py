from pydantic import BaseModel
import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/{userId}/get_all_messages")
async def get_all_messages(userId: int, db: Session = Depends(get_db)):
    try:
        messages = await db.scalars(
            select(DB_models.message)
            .where(or_(DB_models.message.fromId == userId, DB_models.message.toId == userId))
        )
        messages = messages.all()

        group_subquery = (
            select(DB_models.mapTable.groupId)
            .where(DB_models.mapTable.userId == userId)
        )
        
        stmt = (
            select(DB_models.groupMessage, DB_models.messageReceipt)
            .join(
                DB_models.messageReceipt, 
                DB_models.groupMessage.id == DB_models.messageReceipt.groupMessageId
            )
            .where(
                DB_models.groupMessage.toId.in_(group_subquery),
                DB_models.groupMessage.fromId == userId
            )
        )
        
        results = await db.execute(stmt)
        groupMessages = results.scalars().all()

        return {"messages": messages, "groupMessages": groupMessages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UsernameUpdateRequest(BaseModel):
    newUsername: str

@router.post("/{userId}/change_username")
async def change_username(userId: int, data: UsernameUpdateRequest, db: Session = Depends(get_db)):
    try:
        await db.execute(
            update(DB_models.user)
            .where(DB_models.user.id == userId)
            .values(username=data.newUsername)
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
