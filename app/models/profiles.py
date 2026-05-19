"""
Profile model — maps to the profiles table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from .base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = Column(Text, nullable=True)
    email: Mapped[str] = Column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
