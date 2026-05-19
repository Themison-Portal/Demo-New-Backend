"""
PatientVisit model — maps to the patient_visits table.
Uses ForeignKeyConstraint for composite FK to trial_patients(patient_id, trial_id).
"""

import uuid
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Text, Time
from sqlalchemy.dialects.postgresql import ENUM, JSON, UUID
from sqlalchemy.orm import Mapped, relationship


from app.models.members import Member
from app.models.trials import Trial
from app.models.patients import Patient


from .base import Base


class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    trial_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    visit_date: Mapped[date] = Column(Date, nullable=False)
    visit_time: Mapped[Optional[time]] = Column(Time, nullable=True)
    visit_type: Mapped[str] = Column(
        ENUM(
            "screening",
            "baseline",
            "follow_up",
            "treatment",
            "assessment",
            "monitoring",
            "adverse_event",
            "unscheduled",
            "study_closeout",
            "withdrawal",
            name="visit_type_enum",
            create_type=False,
        ),
        nullable=False,
        default="follow_up",
    )
    status: Mapped[str] = Column(
        ENUM(
            "scheduled",
            "in_progress",
            "completed",
            "cancelled",
            "no_show",
            "rescheduled",
            name="visit_status_enum",
            create_type=False,
        ),
        nullable=False,
        default="scheduled",
    )
    duration_minutes: Mapped[Optional[int]] = Column(Integer, nullable=True)
    visit_number: Mapped[Optional[int]] = Column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    next_visit_date: Mapped[Optional[date]] = Column(Date, nullable=True)
    location: Mapped[Optional[str]] = Column(Text, nullable=True)
    actual_date: Mapped[Optional[date]] = Column(Date, nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    cost_data: Mapped[Optional[dict]] = Column(JSON, default=dict)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    trial: Mapped["Trial"] = relationship("Trial", foreign_keys=[trial_id])
    doctor: Mapped["Member"] = relationship("Member", foreign_keys=[doctor_id])
    activities: Mapped[list["VisitActivity"]] = relationship(
        "VisitActivity", back_populates="visit", cascade="all, delete-orphan"
    )
