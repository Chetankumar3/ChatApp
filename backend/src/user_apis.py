from pydantic import BaseModel
import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/{UserId}/get_all_messages")
async def get_all_messages(UserId: int, db: Session = Depends(get_db)):
    try:
        Messages = await db.scalars(
            select(DB_models.Message)
            .where(or_(DB_models.Message.FromId==UserId, DB_models.Message.ToId==UserId))
        )
        Messages = Messages.all()

        group_subquery = (
            select(DB_models.MapTable.GroupId)
            .where(DB_models.MapTable.UserId == UserId)
        )
        
        stmt = (
            select(DB_models.GroupMessage, DB_models.MessageReceipt)
            .join(
                DB_models.MessageReceipt, 
                DB_models.GroupMessage.Id == DB_models.MessageReceipt.GroupMessageId
            )
            .where(
                DB_models.GroupMessage.ToId.in_(group_subquery),
                DB_models.GroupMessage.FromId == UserId
            )
        )
        
        results = await db.execute(stmt)
        GroupMessages = results.scalars().all()

        return {"Messages": Messages, "GroupMessages": GroupMessages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UsernameUpdateRequest(BaseModel):
    NewUsername: str

@router.post("/{UserId}/change_username")
async def change_username(UserId: int, data: UsernameUpdateRequest, db: Session = Depends(get_db)):
    try:
        await db.execute(
            update(DB_models.User)
            .where(DB_models.User.Id == UserId)
            .values(Username=data.NewUsername)
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
