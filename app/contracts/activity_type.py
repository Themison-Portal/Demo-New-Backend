from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class TrialActivityTypeResponse(BaseModel):
    id: UUID
    trial_id: UUID
    activity_id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    is_custom: Optional[bool] = True
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TrialActivityTypeCreate(BaseModel):
    activity_id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    is_custom: Optional[bool] = True
