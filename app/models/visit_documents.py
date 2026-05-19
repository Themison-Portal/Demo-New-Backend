"""
VisitDocument model — maps to the visit_documents table.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ARRAY, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class VisitDocument(Base):
    __tablename__ = "visit_documents"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    document_name: Mapped[str] = Column(Text, nullable=False)
    document_type: Mapped[str] = Column(
        ENUM(
            "visit_note", "lab_results", "blood_test", "vital_signs", "invoice",
            "billing_statement", "medication_log", "adverse_event_form", "assessment_form",
            "imaging_report", "procedure_note", "data_export", "consent_form",
            "insurance_document", "other",
            name="visit_document_type_enum", create_type=False,
        ),
        nullable=False,
    )
    file_type: Mapped[Optional[str]] = Column(Text, nullable=True)
    document_url: Mapped[str] = Column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = Column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = Column(String(100), nullable=True)
    version: Mapped[Optional[int]] = Column(Integer, default=1)
    is_latest: Mapped[Optional[bool]] = Column(Boolean, default=True)
    uploaded_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    upload_date: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = Column(ARRAY(Text), nullable=True)
    amount: Mapped[Optional[Decimal]] = Column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = Column(String(3), default="USD")
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    visit: Mapped["PatientVisit"] = relationship("PatientVisit", foreign_keys=[visit_id])
