"""
CollaborationThread + CollaborationThreadMessage models.
Maps to collaboration_threads and collaboration_thread_messages tables.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped

from app.models.base import Base


class CollaborationThread(Base):
    __tablename__ = "collaboration_threads"

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
    title: Mapped[str] = Column(Text, nullable=False)
    thread_type: Mapped[str] = Column(Text, nullable=False, default="general")
    anchors: Mapped[List] = Column(JSONB, nullable=False, default=[])
    is_resolved: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_summary: Mapped[Optional[str]] = Column(Text, nullable=True)
    ai_draft_summary: Mapped[Optional[str]] = Column(Text, nullable=True)
    created_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    messages = relationship(
        "CollaborationThreadMessage",
        back_populates="thread",
        order_by="CollaborationThreadMessage.created_at",
        lazy="select",
    )


class CollaborationThreadMessage(Base):
    __tablename__ = "collaboration_thread_messages"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("collaboration_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = Column(Text, nullable=False, default="user")
    content: Mapped[str] = Column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    thread = relationship("CollaborationThread", back_populates="messages")
    sender = relationship("Profile", foreign_keys=[sender_id], lazy="select")
