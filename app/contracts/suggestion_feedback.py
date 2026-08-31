from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.suggestion_feedback import FeedbackStatus


class SuggestionFeedbackCreate(BaseModel):
    org_id: str
    trial_id: Optional[UUID] = None
    target_type: str
    target_id: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    label: str
    status: FeedbackStatus
    comment: Optional[str] = None


class SuggestionFeedbackResponse(BaseModel):
    id: UUID
    org_id: str
    user_id: UUID
    trial_id: Optional[UUID]
    target_type: str
    target_id: Optional[str]
    question: Optional[str]
    answer: Optional[str]
    label: str
    status: FeedbackStatus
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True