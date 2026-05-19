"""
Contracts for the QA repository.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class QAItemBase(BaseContract):
    question: str
    answer: str
    trial_id: UUID
    tags: Optional[List[str]] = None
    is_verified: Optional[bool] = False
    source: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None


class QAItemCreate(QAItemBase):
    pass


class QAItemUpdate(BaseContract):
    question: Optional[str] = None
    answer: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None


class QAItemResponse(QAItemBase, TimestampedContract):
    id: UUID
    created_by: Optional[UUID] = None
    # Joined fields
    creator_name: Optional[str] = None
    creator_email: Optional[str] = None
