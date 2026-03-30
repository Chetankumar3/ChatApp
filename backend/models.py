from pydantic import BaseModel
from typing import Optional

class message(BaseModel):
    id: int
    type: str # "direct_message" or "group_message"
    fromId: int
    toId: int
    message: str
    sentAt: str
    receivedAt: Optional[str] = None

class group(BaseModel):
    id: int
    name: str
    description: str
    displayPictureUrl: str
    members = Optional[list[str]] = None

class user(BaseModel):
    id: int
    username: str
    name: str
    mobileNumber: str
    email: str
    displayPictureUrl: str