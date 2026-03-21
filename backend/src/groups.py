from pydantic import BaseModel
import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import Session
from database import get_db
import DB_models
from models import Group

router = APIRouter()

class groupCreation(BaseModel):
    message: str
    groupId: int

class APIRsponse(BaseModel):
    success: bool
    message: str


@router.put("/create", response_model=groupCreation)
async def create_group(group: Group, db: Session = Depends(get_db)):
    try:
        new_group = DB_models.group(**group.model_dump(exclude_unset=True))
        db.add(new_group)
        await db.commit()
        await db.refresh(new_group)

        return {"message": "Group created successfully", "group_id": new_group.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/update/{group_id}", response_model=APIRsponse)
async def update_group(group_id: int, group: Group, db: Session = Depends(get_db)):
    try:
        group_exists = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
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

@router.post("/add_member/{group_id}/{user_id}", response_model=APIRsponse)
async def add_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        group_exists = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
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

@router.delete("/delete/{group_id}", response_model=APIRsponse)
async def delete_group(group_id: int, db: Session = Depends(get_db)):
    try:
        db_group = db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        await db.execute(
            delete(DB_models.mapTable)
            .where(DB_models.mapTable.groupId == group_id)
        )

        db.delete(db_group)
        await db.commit()
        return {"success": True, "message": "Group deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))