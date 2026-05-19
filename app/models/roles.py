"""
Role model — maps to the roles table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped

from .base import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = Column(Text, nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    permission_level: Mapped[str] = Column(
        ENUM("read", "edit", "admin", name="permission_level", create_type=False),
        nullable=False,
        default="read",
    )
    organization_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[Optional[UUID]] = Column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
