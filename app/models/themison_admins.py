"""
Themison admin model — maps to the themison_admins table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from .base import Base


class ThemisonAdmin(Base):
    __tablename__ = "themison_admins"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = Column(Text, nullable=False)
    name: Mapped[Optional[str]] = Column(Text, nullable=True)
    active: Mapped[Optional[bool]] = Column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[Optional[UUID]] = Column(UUID(as_uuid=True), nullable=True)
