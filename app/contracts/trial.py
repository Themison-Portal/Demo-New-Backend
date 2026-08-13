"""
Contracts for trials.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class _TrialFeFields(BaseContract):
    """FE-owned trial fields migrated from the FE MySQL `trials` table."""
    slug: Optional[str] = None
    demo_mode: Optional[str] = None
    protocol_number: Optional[str] = None
    investigational_product: Optional[str] = None
    indication: Optional[str] = None
    nct_number: Optional[str] = None
    current_version: Optional[str] = None
    amendment_version: Optional[str] = None
    release_date: Optional[str] = None
    sample_size: Optional[str] = None
    number_of_sites: Optional[str] = None
    study_duration: Optional[str] = None
    study_design_type: Optional[str] = None
    primary_objective: Optional[str] = None
    primary_endpoint: Optional[str] = None
    principal_investigator: Optional[str] = None
    enrolled_patients: Optional[int] = None
    target_patients: Optional[int] = None
    completion_percentage: Optional[int] = None


class TrialBase(_TrialFeFields):
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


class TrialUpdate(_TrialFeFields):
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
