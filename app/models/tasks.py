# app/models/tasks.py
from sqlalchemy import Column, String, DateTime, ForeignKey, text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base  # your declarative base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    trial_id = Column(UUID(as_uuid=True), ForeignKey("trials.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default="todo")
    priority = Column(String, nullable=True)
    category = Column(String, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    visit_id = Column(
        UUID(as_uuid=True), ForeignKey("patient_visits.id"), nullable=True
    )
    activity_type_id = Column(
        UUID(as_uuid=True), ForeignKey("activity_types.id"), nullable=True
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # relationships
    # trial = relationship("Trial", back_populates="tasks")
    # assigned_user = relationship("Member", back_populates="tasks")
    # patient = relationship("Patient", back_populates="tasks")
    # visit = relationship("Visit", back_populates="tasks")
    # activity_type = relationship("ActivityType", back_populates="tasks")
