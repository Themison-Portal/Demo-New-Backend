"""
Trial model — maps to the trials table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
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

    # ── FE-owned trial fields migrated from the FE MySQL `trials` table ──
    # `slug` is the bare id the FE client routes by (e.g. "cardiac-a2b3c", "1");
    # `demo_mode` partitions the three demo datasets (sample|full|building).
    # Together with organization_id they uniquely identify a trial — that's how
    # the BFF resolves the client's slug to this row's UUID.
    slug: Mapped[Optional[str]] = Column(Text, nullable=True, index=True)
    demo_mode: Mapped[Optional[str]] = Column(Text, nullable=True, index=True)
    protocol_number: Mapped[Optional[str]] = Column(Text, nullable=True)
    investigational_product: Mapped[Optional[str]] = Column(Text, nullable=True)
    indication: Mapped[Optional[str]] = Column(Text, nullable=True)
    nct_number: Mapped[Optional[str]] = Column(Text, nullable=True)
    current_version: Mapped[Optional[str]] = Column(Text, nullable=True)
    amendment_version: Mapped[Optional[str]] = Column(Text, nullable=True)
    release_date: Mapped[Optional[str]] = Column(Text, nullable=True)
    sample_size: Mapped[Optional[str]] = Column(Text, nullable=True)
    number_of_sites: Mapped[Optional[str]] = Column(Text, nullable=True)
    study_duration: Mapped[Optional[str]] = Column(Text, nullable=True)
    study_design_type: Mapped[Optional[str]] = Column(Text, nullable=True)
    primary_objective: Mapped[Optional[str]] = Column(Text, nullable=True)
    primary_endpoint: Mapped[Optional[str]] = Column(Text, nullable=True)
    principal_investigator: Mapped[Optional[str]] = Column(Text, nullable=True)
    enrolled_patients: Mapped[Optional[int]] = Column(Integer, nullable=True)
    target_patients: Mapped[Optional[int]] = Column(Integer, nullable=True)
    completion_percentage: Mapped[Optional[int]] = Column(Integer, nullable=True)
