"""
Organization model — maps to the organizations table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from .base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = Column(Text, nullable=False)
    created_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("themison_admins.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    onboarding_completed: Mapped[Optional[bool]] = Column(Boolean, default=False)
    # NEW flag added to enable/disable support for an organization. This allows us to turn off support for specific organizations without deleting them.
    support_enabled: Mapped[bool] = Column(Boolean, default=True)
    # Flag to track if the organization is currently active
    is_active: Mapped[bool] = Column(Boolean, default=True)
