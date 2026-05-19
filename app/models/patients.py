"""
Patient model — maps to the patients table.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from .base import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_code: Mapped[str] = Column(Text, nullable=False)
    organization_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    date_of_birth: Mapped[Optional[date]] = Column(Date, nullable=True)
    gender: Mapped[Optional[str]] = Column(Text, nullable=True)
    first_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    phone_number: Mapped[Optional[str]] = Column(Text, nullable=True)
    email: Mapped[Optional[str]] = Column(Text, nullable=True)
    street_address: Mapped[Optional[str]] = Column(Text, nullable=True)
    city: Mapped[Optional[str]] = Column(Text, nullable=True)
    state_province: Mapped[Optional[str]] = Column(Text, nullable=True)
    postal_code: Mapped[Optional[str]] = Column(Text, nullable=True)
    country: Mapped[Optional[str]] = Column(Text, default="United States")
    emergency_contact_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = Column(Text, nullable=True)
    emergency_contact_relationship: Mapped[Optional[str]] = Column(Text, nullable=True)
    height_cm: Mapped[Optional[Decimal]] = Column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[Optional[Decimal]] = Column(Numeric(5, 2), nullable=True)
    blood_type: Mapped[Optional[str]] = Column(Text, nullable=True)
    medical_history: Mapped[Optional[str]] = Column(Text, nullable=True)
    current_medications: Mapped[Optional[str]] = Column(Text, nullable=True)
    known_allergies: Mapped[Optional[str]] = Column(Text, nullable=True)
    primary_physician_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    primary_physician_phone: Mapped[Optional[str]] = Column(Text, nullable=True)
    insurance_provider: Mapped[Optional[str]] = Column(Text, nullable=True)
    insurance_policy_number: Mapped[Optional[str]] = Column(Text, nullable=True)
    consent_signed: Mapped[Optional[bool]] = Column(Boolean, default=False)
    consent_date: Mapped[Optional[date]] = Column(Date, nullable=True)
    screening_notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    is_active: Mapped[Optional[bool]] = Column(Boolean, default=True)
