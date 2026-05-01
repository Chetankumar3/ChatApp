from pydantic import BaseModel
from typing import Optional

class message(BaseModel):
    id: int
    type: str  # "direct_message" or "group_message"
    fromId: int
    toId: int
    message: str
    sentAt: str
    receivedAt: Optional[str] = None