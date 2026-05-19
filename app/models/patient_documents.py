"""
PatientDocument model — maps to the patient_documents table.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ARRAY, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped

from .base import Base


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    document_name: Mapped[str] = Column(Text, nullable=False)
    document_type: Mapped[str] = Column(
        ENUM(
            "medical_record", "lab_result", "imaging", "consent_form", "assessment",
            "questionnaire", "adverse_event_report", "medication_record", "visit_note",
            "discharge_summary", "other",
            name="patient_document_type_enum", create_type=False,
        ),
        nullable=False,
    )
    document_url: Mapped[str] = Column(String, nullable=False)
    patient_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    uploaded_by: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    status: Mapped[Optional[str]] = Column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = Column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = Column(String, nullable=True)
    version: Mapped[Optional[int]] = Column(Integer, default=1)
    is_latest: Mapped[Optional[bool]] = Column(Boolean, default=True)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = Column(ARRAY(Text), nullable=True)
