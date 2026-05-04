from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import DB_models
from ..database import get_db
from .login import get_current_user

router = APIRouter()


@router.get("/get_all_users")
async def get_all_users(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = await db.scalars(select(DB_models.user))
        await db.close()
        return {"users": result.all()}
    except Exception:
        await db.close()
        raise
