import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/get_all_users")
async def get_all_users(db: Session = Depends(get_db)):
    try:
        result = await db.execute(select(DB_models.user.id, DB_models.user.username))
        return {"users": result.mappings().all()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))