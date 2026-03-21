from pydantic import BaseModel

class Message(BaseModel):
    id: int
    type: int # 0=personal, 1=group
    fromId: int
    toId: int
    message: str
    sentAt: str
    receivedAt: str

class Group(BaseModel):
    id: int
    name: str
    description: str
    displayPictureUrl: str