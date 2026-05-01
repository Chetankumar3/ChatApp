import os
import asyncio
import secrets

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import DB_models, models
from ..database import get_db

load_dotenv()
WEBCLIENT_ID = os.getenv("WEBCLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")
router = APIRouter()
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def create_jwt_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=2)
    return jwt.encode({"user_id": user_id, "exp": expire}, JWT_SECRET, algorithm=ALGORITHM)


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.execute(select(DB_models.user).where(DB_models.user.id == user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/login/google")
async def google_login(data: models.GoogleTokenData, db: Session = Depends(get_db)):
    try:
        id_info = await asyncio.to_thread(
            id_token.verify_oauth2_token, data.token, requests.Request(), WEBCLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")
    except Exception as e:
        print(f"Google Verify Error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

    try:
        user_id = await db.execute(
            select(DB_models.oAuthTable.userId).where(
                DB_models.oAuthTable.oauthId == id_info["sub"]
            )
        )
        user_id = user_id.scalar_one_or_none()

        if not user_id:
            user_ = DB_models.user(
                name=id_info["name"],
                username=id_info["name"][:4].lower() + secrets.token_hex(3)[:5],
                email=id_info["email"],
                displayPictureUrl=id_info.get("picture"),
            )
            db.add(user_)
            await db.flush()
            await db.refresh(user_)

            db.add(DB_models.oAuthTable(userId=user_.id, oauthId=id_info["sub"]))
            await db.commit()

            return {"token": create_jwt_token(user_.id), "isNewUser": True}

        return {"token": create_jwt_token(user_id), "isNewUser": False}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/credentials")
async def credentials_login(data: models.LoginCredentials, db: Session = Depends(get_db)):
    try:
        password_entry = await db.execute(
            select(DB_models.passwords)
            .join(DB_models.user, DB_models.passwords.userId == DB_models.user.id)
            .where(DB_models.user.username == data.username)
        )
        password_entry = password_entry.scalar_one_or_none()

        if not password_entry:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if data.username[:4] == "Test":
            if data.password == password_entry.hashedPassword:
                return {"token": create_jwt_token(password_entry.userId), "isNewUser": False}
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not await asyncio.to_thread(
            bcrypt.checkpw,
            data.password.encode("utf-8"),
            password_entry.hashedPassword.encode("utf-8"),
        ):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        return {"token": create_jwt_token(password_entry.userId), "isNewUser": False}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register(data: models.RegisterCredentials, db: Session = Depends(get_db)):
    try:
        existing = await db.execute(
            select(DB_models.passwords).where(
                DB_models.passwords.userId == select(DB_models.user.id).where(
                    DB_models.user.username == data.username
                ).scalar_subquery()
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already exists, Login or Change username")

        user_ = DB_models.user(name=data.name, email=data.email, username=data.username)
        db.add(user_)
        await db.flush()
        await db.refresh(user_)

        if data.username[:4] != "Test":
            hashed = await asyncio.to_thread(
                bcrypt.hashpw, data.password.encode("utf-8"), bcrypt.gensalt()
            )
            hashed_str = hashed.decode("utf-8")
        else:
            hashed_str = data.password

        db.add(DB_models.passwords(userId=user_.id, hashedPassword=hashed_str))
        await db.commit()

        return {"token": create_jwt_token(user_.id), "isNewUser": False}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
