"""
Contracts for visit activities.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional
from .base import BaseContract, TimestampedContract


class VisitActivityBase(BaseContract):
    visit_id: UUID
    activity_name: str
    status: str = "pending"  # "pending", "completed", "not_applicable"


class VisitActivityUpdate(BaseContract):
    status: str


class VisitActivityResponse(VisitActivityBase, TimestampedContract):
    id: UUID
