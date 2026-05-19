"""
Contracts for trials.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class TrialBase(BaseContract):
    name: str
    phase: str
    location: str
    sponsor: str
    description: Optional[str] = None
    status: Optional[str] = "planning"
    image_url: Optional[str] = None
    study_start: Optional[str] = None
    estimated_close_out: Optional[str] = None
    budget_data: Optional[Dict[str, Any]] = None


class TrialCreate(TrialBase):
    pass


class TrialUpdate(BaseContract):
    name: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    location: Optional[str] = None
    sponsor: Optional[str] = None
    status: Optional[str] = None
    image_url: Optional[str] = None
    study_start: Optional[str] = None
    estimated_close_out: Optional[str] = None
    budget_data: Optional[Dict[str, Any]] = None


class TrialResponse(TrialBase, TimestampedContract):
    id: UUID
    organization_id: UUID
    created_by: Optional[UUID] = None


class TrialMemberAssignment(BaseContract):
    member_id: UUID
    role_id: UUID


class TrialPendingMemberAssignment(BaseContract):
    invitation_id: UUID
    role_id: UUID


class TrialWithAssignmentsCreate(TrialCreate):
    members: List[TrialMemberAssignment] = []
    pending_members: List[TrialPendingMemberAssignment] = []
