"""
VisitActivity model — maps to visit_activities table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.models.patient_visits import PatientVisit

from .base import Base


class VisitActivity(Base):
    __tablename__ = "visit_activities"

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    visit_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("patient_visits.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_name: Mapped[str] = Column(String, nullable=False)
    status: Mapped[str] = Column(
        String, nullable=False, default="pending"
    )  # "pending", "completed", "not_applicable"
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to visit
    visit: Mapped["PatientVisit"] = relationship(
        "PatientVisit", back_populates="activities"
    )
