"""
TrialMemberPending model — maps to the trial_members_pending table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class TrialMemberPending(Base):
    __tablename__ = "trial_members_pending"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False
    )
    invitation_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("invitations.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    invited_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Relationships
    trial: Mapped["Trial"] = relationship("Trial", foreign_keys=[trial_id])
    invitation: Mapped["Invitation"] = relationship("Invitation", foreign_keys=[invitation_id])
    role: Mapped["Role"] = relationship("Role", foreign_keys=[role_id])
