# app/models/task_dependencies.py
from sqlalchemy import Column, String, ForeignKey, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    source_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    target_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String, default="finish_to_start")
    condition_label = Column(String, nullable=True)
    is_cross_phase = Column(Boolean, default=False)
