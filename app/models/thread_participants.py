from datetime import datetime
from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class ThreadParticipant(Base):
    __tablename__ = "thread_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # thread_id = Column(
    #     UUID(as_uuid=True), ForeignKey("chat_threads.id"), nullable=False
    # )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("members.profile_id"), nullable=False
    )
    last_read_message_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True
    )

    # # Relationships
    # thread = relationship("ChatThread", back_populates="participants")
