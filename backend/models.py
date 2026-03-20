from pydantic import BaseModel

class Message(BaseModel):
    Id: int
    Type: int # 0=personal, 1=group
    FromId: int
    ToId: int
    Message: str
    SentAt: str
    ReceivedAt: str

class TokenData(BaseModel):
    Token: str