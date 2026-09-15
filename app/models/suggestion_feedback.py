from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base


class FeedbackStatus(str, enum.Enum):
    good = "good"
    needs_work = "needs_work"


class SuggestionFeedback(Base):
    __tablename__ = "suggestion_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=True)

    target_type = Column(String, nullable=False)   # e.g. "chat_response", "type_scale"
    target_id = Column(String, nullable=True)        
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)

    label = Column(String, nullable=False)           
    status = Column(Enum(FeedbackStatus), nullable=False)
    comment = Column(Text, nullable=True)              

    created_at = Column(DateTime, default=datetime.utcnow)