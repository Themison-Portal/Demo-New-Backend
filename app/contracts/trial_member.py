"""
Contracts for trial members and pending trial members.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from .base import BaseContract


class TrialMemberBase(BaseContract):
    trial_id: UUID
    member_id: UUID
    role_id: UUID


class TrialMemberCreate(TrialMemberBase):
    start_date: Optional[date] = None


class TrialMemberResponse(TrialMemberBase):
    id: UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    # Joined fields
    member_name: Optional[str] = None
    member_email: Optional[str] = None
    role_name: Optional[str] = None
    permission_level: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    settings: Optional[dict] = None


class PendingMemberBase(BaseContract):
    trial_id: UUID
    invitation_id: UUID
    role_id: UUID


class PendingMemberCreate(PendingMemberBase):
    notes: Optional[str] = None


class PendingMemberResponse(PendingMemberBase):
    id: UUID
    invited_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    # Joined fields from invitation
    invitation_email: Optional[str] = None
    invitation_name: Optional[str] = None
    invitation_status: Optional[str] = None
    role_name: Optional[str] = None
    permission_level: Optional[str] = None
