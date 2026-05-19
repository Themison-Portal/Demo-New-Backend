"""
QARepository model — maps to the qa_repository table.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class QARepositoryItem(Base):
    __tablename__ = "qa_repository"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = Column(Text, nullable=False)
    answer: Mapped[str] = Column(Text, nullable=False)
    created_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    tags: Mapped[Optional[List[str]]] = Column(ARRAY(Text), nullable=True)
    is_verified: Mapped[Optional[bool]] = Column(Boolean, default=False)
    source: Mapped[Optional[str]] = Column(Text, nullable=True)
    sources: Mapped[Optional[dict]] = Column(JSON, default=list)

    # Relationships
    trial: Mapped["Trial"] = relationship("Trial", foreign_keys=[trial_id])
    creator: Mapped[Optional["Member"]] = relationship("Member", foreign_keys=[created_by])
