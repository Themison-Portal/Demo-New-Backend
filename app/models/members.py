"""
Member model — maps to the members table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = Column(Text, nullable=False)
    email: Mapped[str] = Column(Text, nullable=False)
    organization_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    profile_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    default_role: Mapped[str] = Column(
        ENUM("admin", "staff", "superadmin", "editor", "viewer", name="organization_member_type", create_type=False),
        nullable=False,
        default="staff",
    )
    invited_by: Mapped[Optional[UUID]] = Column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    onboarding_completed: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", foreign_keys=[profile_id])
    organization: Mapped["Organization"] = relationship("Organization", foreign_keys=[organization_id])
