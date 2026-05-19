from uuid import UUID
from pydantic import BaseModel
from typing import Optional


class ThreadParticipantResponse(BaseModel):
    thread_id: UUID
    user_id: UUID
    last_read_message_id: Optional[UUID]
