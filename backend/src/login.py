import os
from dotenv import load_dotenv
load_dotenv()

import DB_models
import models
from database import get_db
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from fastapi import Depends
from google.auth.transport import requests
from pydantic import BaseModel

WEBCLIENT_ID = os.getenv("WEBCLIENT_ID")
router = APIRouter()

class TokenData(BaseModel):
    token: str

@router.post("/login")
async def login(data: models.TokenData, db: Session = Depends(get_db)):
    IdInfo = None
    try:
        IdInfo = await asyncio.to_thread(
            id_token.verify_oauth2_token, 
            data.Token, 
            requests.Request(), 
            WEBCLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")
    except Exception as e:
        print(f"Google Verify Error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

    try:
        print(IdInfo)

        user_id = await db.execute(
                        select(DB_models.oAuthTable.userId)
                        .where(DB_models.oAuthTable.oauthId == IdInfo["sub"])
                    )    
        user_id = user_id.scalar_one_or_none()

        if not user_id:
            user_ = DB_models.user(
                name=IdInfo["name"],
                email=IdInfo["email"],
                displayPictureUrl=IdInfo.get("picture")
            )

            db.add(user_)
            await db.flush()
            await db.refresh(user_)

            oauth_ = DB_models.oAuthTable(
                userId=user_.id,
                oauthId=IdInfo["sub"]
            )

            db.add(oauth_)
            await db.commit()
            
            return {"userId": user_.id}

        return {"userId": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))