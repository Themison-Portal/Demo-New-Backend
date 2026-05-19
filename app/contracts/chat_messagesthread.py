from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChatMessageCreate(BaseModel):
    thread_id: UUID
    content: str
    role: str = "user"


class ChatMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    content: str
    role: str
    sent_at: datetime
