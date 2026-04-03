import DB_models
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/get_all_users")
async def get_all_users(db: Session = Depends(get_db)):
    try:
        result = await db.scalars(select(DB_models.user))
        return {"users": result.all()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))