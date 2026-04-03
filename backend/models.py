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
    id: Optional[int] = None
    name: str
    description: str
    displayPictureUrl: Optional[str] = None
    members: Optional[list[int]] = None

class user(BaseModel):
    id: int
    username: Optional[str] = None
    name: str
    mobileNumber: Optional[str] = None
    email: str
    displayPictureUrl: str