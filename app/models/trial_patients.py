"""
TrialPatient model — maps to the trial_patients table.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class TrialPatient(Base):
    __tablename__ = "trial_patients"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("trials.id"), nullable=False
    )
    patient_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    enrollment_date: Mapped[Optional[date]] = Column(Date, default=date.today)
    status: Mapped[Optional[str]] = Column(Text, default="enrolled")
    randomization_code: Mapped[Optional[str]] = Column(Text, nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    assigned_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    cost_data: Mapped[Optional[dict]] = Column(JSON, default=dict)
    patient_data: Mapped[Optional[dict]] = Column(JSON, default=dict)

    # Relationships
    trial: Mapped["Trial"] = relationship("Trial", foreign_keys=[trial_id])
    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
