from pydantic import BaseModel
import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import Session
from database import get_db
import DB_models, models

router = APIRouter()

class groupCreation(BaseModel):
    message: str
    groupId: int

class APIRsponse(BaseModel):
    success: bool
    message: str

@router.put("/create/{creator_id}", response_model=groupCreation)
async def create_group(data: models.group, creator_id: int, db: Session = Depends(get_db)):
    try:
        new_group = DB_models.group(**data.model_dump(exclude_unset=True, exclude="members"))
        db.add(new_group)
        await db.commit()
        await db.refresh(new_group)

        data.members.append(creator_id)
        data.members = list(dict.fromkeys(data.members or []))
        for user_id in data.members:
            map_table_entry = DB_models.mapTable(groupId=new_group.id, userId=user_id, admin=(user_id == creator_id))
            db.add(map_table_entry)

        await db.commit()
        return {"message": "Group created successfully", "groupId": new_group.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/get_group_info/{group_id}", response_model=models.group)
async def get_group_info(group_id: int, db: Session = Depends(get_db)):
    try:
        group_info = await db.execute(
            select(DB_models.group)
            .where(DB_models.group.id == group_id)
        )
        group_info = group_info.scalar_one_or_none()

        if not group_info:
            raise HTTPException(status_code=404, detail="Group not found")
        
        user_ids = await db.execute(
            select(DB_models.mapTable.userId)
            .where(DB_models.mapTable.groupId == group_id)
        )
        group_info.members = user_ids.scalars().all()

        return group_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.put("/update/{modifier_id}/{group_id}", response_model=APIRsponse)
async def update_group(modifier_id: int, group_id: int, group: models.group, db: Session = Depends(get_db)):
    try:
        is_admin = await db.scalar(
            select(DB_models.mapTable)
            .where(and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == modifier_id, DB_models.mapTable.admin == True))
        )

        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admins can update the group")

        group_exists = db.scalar(
            select(DB_models.group)
            .where(DB_models.group.id == group_id)
        )
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        await db.execute(
            update(DB_models.group)
            .where(DB_models.group.id == group_id)
            .values(**group.model_dump(exclude_unset=True))
        )

        await db.commit()
        return {"success": True, "message": "Group updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/add_member/{modifier_id}/{group_id}", response_model=APIRsponse)
async def add_member(group_id: int, modifier_id: int, user_ids: list[int], db: Session = Depends(get_db)):
    try:
        is_admin = await db.scalar(
            select(DB_models.mapTable)
            .where(and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == modifier_id, DB_models.mapTable.admin == True))
        )

        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admins can update the group")
        
        group_exists = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        for user_id in user_ids:
            map_table_entry = DB_models.mapTable(groupId=group_id, userId=user_id)
            db.add(map_table_entry)
        await db.commit()

        return {"success": True, "message": "Member added successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/exit/{group_id}/{user_id}", response_model=APIRsponse)
async def exit_group(group_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        group_exists = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        user_in_group = db.scalar(
            select(DB_models.mapTable)
            .where(and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == user_id))
        )
        if not user_in_group:
            raise HTTPException(status_code=400, detail="User not in group")

        db.delete(user_in_group)
        await db.commit()
        return {"success": True, "message": "User exited group successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{modifier_id}/{group_id}", response_model=APIRsponse)
async def delete_group(modifier_id: int, group_id: int, db: Session = Depends(get_db)):
    try:
        is_admin = await db.scalar(
            select(DB_models.mapTable)
            .where(and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == modifier_id, DB_models.mapTable.admin == True))
        )
    
        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admins can delete the group")
        
        db_group = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        await db.execute(
            delete(DB_models.mapTable)
            .where(DB_models.mapTable.groupId == group_id)
        )
        await db.execute(
            delete(DB_models.messageReceipt)
            .where(DB_models.messageReceipt.groupMessageId.in_(select(DB_models.groupMessage.id).where(DB_models.groupMessage.toId == group_id)))
        )
        await db.execute(
            delete(DB_models.groupMessage)
            .where(DB_models.groupMessage.toId == group_id)
        )

        db.delete(db_group)
        await db.commit()
        return {"success": True, "message": "Group deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))