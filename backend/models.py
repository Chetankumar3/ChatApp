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

class user(BaseModel):
    id: int
    username: Optional[str] = None
    name: str
    mobileNumber: Optional[str] = None
    email: Optional[str] = None
    displayPictureUrl: Optional[str] = None
    
class group(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    displayPictureUrl: Optional[str] = None
    members: list[user]

    model_config = {"from_attributes": True}

# Login models
class LoginCredentials(BaseModel):
    username: str
    password: str

class RegisterCredentials(BaseModel):
    username: str
    password: str
    name: str
    email: str

class GoogleTokenData(BaseModel):
    token: str

# Group models
class groupCreationInput(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    displayPictureUrl: Optional[str] = None
    members: Optional[list[int]] = None

class groupCreationOutput(BaseModel):
    message: str
    groupId: int

class groupUpdationInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    displayPictureUrl: Optional[str] = None
    members: Optional[list[int]] = None

class APIResponse(BaseModel):
    success: bool
    message: str

# User models
class UsernameUpdateRequest(BaseModel):
    newUsername: str