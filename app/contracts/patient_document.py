"""
Contracts for patient documents.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class PatientDocumentBase(BaseContract):
    document_name: str
    document_type: str
    document_url: str
    patient_id: Optional[UUID] = None
    uploaded_by: Optional[UUID] = None
    status: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    version: Optional[int] = 1
    is_latest: Optional[bool] = True
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class PatientDocumentCreate(PatientDocumentBase):
    pass


class PatientDocumentUpdate(BaseContract):
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    document_url: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_latest: Optional[bool] = None


class PatientDocumentResponse(PatientDocumentBase, TimestampedContract):
    id: UUID
