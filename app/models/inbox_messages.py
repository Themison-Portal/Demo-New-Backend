"""
InboxMessage model — maps to inbox_messages table.
Email-style messages in the Collaboration Hub inbox.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Text, Boolean, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped

from app.models.base import Base


class InboxMessage(Base):
    __tablename__ = "inbox_messages"

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
    owner_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_name: Mapped[str] = Column(Text, nullable=False)
    sender_email: Mapped[Optional[str]] = Column(Text, nullable=True)
    to_addresses: Mapped[List[str]] = Column(ARRAY(Text), nullable=False, default=[])
    cc_addresses: Mapped[List[str]] = Column(ARRAY(Text), nullable=False, default=[])
    subject: Mapped[str] = Column(Text, nullable=False)
    body: Mapped[str] = Column(Text, nullable=False)
    ai_summary: Mapped[Optional[str]] = Column(Text, nullable=True)
    labels: Mapped[List[str]] = Column(ARRAY(Text), nullable=False, default=[])
    folder: Mapped[str] = Column(Text, nullable=False, default="inbox")
    is_read: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    related_thread_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("collaboration_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
