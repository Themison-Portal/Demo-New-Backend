"""
Trial model — maps to the trials table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped

from .base import Base


class Trial(Base):
    __tablename__ = "trials"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = Column(Text, nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    phase: Mapped[str] = Column(Text, nullable=False)
    location: Mapped[str] = Column(Text, nullable=False)
    sponsor: Mapped[str] = Column(Text, nullable=False)
    status: Mapped[Optional[str]] = Column(Text, default="planning")
    image_url: Mapped[Optional[str]] = Column(Text, nullable=True)
    study_start: Mapped[Optional[str]] = Column(Text, nullable=True)
    estimated_close_out: Mapped[Optional[str]] = Column(Text, nullable=True)
    organization_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[Optional[UUID]] = Column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    budget_data: Mapped[Optional[dict]] = Column(JSON, default=dict)
    # Add this field for visit schedule template
    visit_schedule_template: Mapped[Optional[dict]] = Column(
        JSON, default=dict, nullable=True
    )
