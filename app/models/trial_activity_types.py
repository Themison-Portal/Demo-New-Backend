from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base


class TrialActivityType(Base):
    __tablename__ = "trial_activity_types"

    id = Column(UUID(as_uuid=True), primary_key=True)
    trial_id = Column(UUID(as_uuid=True), ForeignKey("trials.id"))
    activity_id = Column(String, nullable=False)

    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    is_custom = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
