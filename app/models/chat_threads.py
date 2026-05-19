from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    trial_id = Column(UUID(as_uuid=True), ForeignKey("trials.id"), nullable=True)
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("members.profile_id"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # # Relationships
    # participants = relationship("ThreadParticipant", back_populates="thread")
    # messages = relationship("ChatMessage", back_populates="thread")
