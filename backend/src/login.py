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

WEBCLIENT_ID = os.getenv("WEBCLIENT_ID")
router = APIRouter()

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

        userid = await db.scalar(
                        select(DB_models.OAuthTable.UserId)
                        .where(DB_models.OAuthTable.OAuthId==IdInfo["sub"])
                    )
    
        if not userid:
            user_ = DB_models.User(
                Name=IdInfo["name"],
                Email=IdInfo["email"],
                ProfilePictureUrl=IdInfo.get("picture")
            )

            db.add(user_)
            await db.flush()
            await db.refresh(user_)

            outh_ = DB_models.OAuthTable(
                UserId=user_.Id,
                OAuthId=IdInfo["sub"]
            )

            db.add(outh_)
            await db.commit()
            
            return {"UserId": user_.Id}

        return {"UserId": userid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))