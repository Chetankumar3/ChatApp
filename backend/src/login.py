import os
from dotenv import load_dotenv
import DB_models
import models
from database import get_db
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt

load_dotenv()
WEBCLIENT_ID = os.getenv("WEBCLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")
router = APIRouter()


def create_jwt_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(hours=2)
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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


async def get_current_websocket_user(
    websocket: WebSocket, db: Session = Depends(get_db)
):
    auth_header = websocket.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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
    IdInfo = None
    try:
        IdInfo = await asyncio.to_thread(
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
                DB_models.oAuthTable.oauthId == IdInfo["sub"]
            )
        )
        user_id = user_id.scalar_one_or_none()

        if not user_id:
            user_ = DB_models.user(
                name=IdInfo["name"],
                email=IdInfo["email"],
                displayPictureUrl=IdInfo.get("picture"),
            )

            db.add(user_)
            await db.flush()
            await db.refresh(user_)

            oauth_ = DB_models.oAuthTable(userId=user_.id, oauthId=IdInfo["sub"])

            db.add(oauth_)
            await db.commit()

            token = create_jwt_token(user_.id)
            return {"token": token, "isNewUser": True}

        token = create_jwt_token(user_id)
        return {"token": token, "isNewUser": False}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/credentials")
async def credentials_login(
    data: models.LoginCredentials, db: Session = Depends(get_db)
):
    try:
        # Find user by username
        password_entry = await db.execute(
            select(DB_models.passwords).where(
                DB_models.passwords.userId == select(DB_models.user.id).where(
                    DB_models.user.username == data.username
                )
            )
        )
        password_entry = password_entry.scalar_one_or_none()

        if not password_entry:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Verify password
        if not bcrypt.checkpw(
            data.password.encode("utf-8"), password_entry.hashedPassword.encode("utf-8")
        ):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_jwt_token(password_entry.userId)
        return {"token": token, "isNewUser": False}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register(data: models.RegisterCredentials, db: Session = Depends(get_db)):
    try:
        # Check if username exists
        existing = await db.execute(
            select(DB_models.passwords).where(
                DB_models.passwords.userId == select(DB_models.user.id).where(
                    DB_models.user.username == data.username
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already exists")

        # Create user
        user_ = DB_models.user(name=data.name, email=data.email, username=data.username)
        db.add(user_)
        await db.flush()
        await db.refresh(user_)

        # Hash password
        hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt())

        # Create password entry
        password_ = DB_models.passwords(
            userId=user_.id,
            hashedPassword=hashed.decode("utf-8"),
        )
        db.add(password_)
        await db.commit()

        token = create_jwt_token(user_.id)
        return {"token": token, "isNewUser": False}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
