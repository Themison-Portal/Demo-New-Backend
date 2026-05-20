"""
DirectMessage model — maps to direct_messages table.
1:1 messages between members in the Collaboration Hub.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from app.models.base import Base


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    trial_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = Column(Text, nullable=False)
    task_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_read: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    sent_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    sender = relationship("Profile", foreign_keys=[sender_id], lazy="select")
    recipient = relationship("Profile", foreign_keys=[recipient_id], lazy="select")
    task = relationship("Task", foreign_keys=[task_id], lazy="select")
