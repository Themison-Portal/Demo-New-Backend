from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid


from .base import Base


# ---------------------
# Saved Response
# ---------------------
class SavedResponse(Base):
    __tablename__ = "responses_archived"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(
        UUID(as_uuid=True), ForeignKey("response_folders.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    org_id = Column(String, nullable=False)
    trial_id = Column(UUID(as_uuid=True), nullable=True)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    question = Column(String, nullable=True)
    answer = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
