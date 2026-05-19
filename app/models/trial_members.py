"""
TrialMember model — maps to the trial_members table.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class TrialMember(Base):
    __tablename__ = "trial_members"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[Optional[date]] = Column(Date, default=date.today)
    end_date: Mapped[Optional[date]] = Column(Date, nullable=True)
    is_active: Mapped[Optional[bool]] = Column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = Column(JSON, default=dict, nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    trial: Mapped["Trial"] = relationship("Trial", foreign_keys=[trial_id])
    member: Mapped["Member"] = relationship("Member", foreign_keys=[member_id])
    role: Mapped["Role"] = relationship("Role", foreign_keys=[role_id])
