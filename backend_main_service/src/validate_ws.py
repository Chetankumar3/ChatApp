import os

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import DB_models
from ..database import get_db

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

internal_router = APIRouter(prefix="/internal")


class WSValidationRequest(BaseModel):
    user_id: int
    token: str


@internal_router.post("/validate-ws")
async def validate_websocket_connection(
    data: WSValidationRequest,
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(data.token, JWT_SECRET, algorithms=["HS256"])
        token_user_id = payload.get("user_id")
        if token_user_id is None or token_user_id != data.user_id:
            raise HTTPException(status_code=401, detail="Token does not match user")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.execute(select(DB_models.user).where(DB_models.user.id == data.user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"valid": True, "user_id": user.id}
