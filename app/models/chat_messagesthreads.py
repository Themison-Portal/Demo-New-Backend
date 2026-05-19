from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # thread_id = Column(
    #     UUID(as_uuid=True), ForeignKey("chat_threads.id"), nullable=False
    # )
    content = Column(String, nullable=False)
    role = Column(String, default="user")
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # # Relationships
    # thread = relationship("ChatThread", back_populates="messages")
