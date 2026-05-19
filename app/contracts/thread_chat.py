from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# -------------------------------
# Thread Contracts
# -------------------------------
class ThreadCreate(BaseModel):
    title: str
    trial_id: Optional[UUID] = None


class ThreadUpdate(BaseModel):
    title: Optional[str] = None


class ThreadResponse(BaseModel):
    id: UUID
    title: str
    trial_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
