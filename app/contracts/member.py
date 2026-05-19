"""
Contracts for members.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class MemberBase(BaseContract):
    name: str
    email: str
    default_role: str
    onboarding_completed: bool = False


class MemberResponse(MemberBase, TimestampedContract):
    id: UUID
    organization_id: UUID
    profile_id: UUID
    invited_by: Optional[UUID] = None
    is_active: Optional[bool] = None
    # Joined fields from profile
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class MemberUpdate(BaseContract):
    name: Optional[str] = None
    default_role: Optional[str] = None
    onboarding_completed: Optional[bool] = None


class MemberTrialAssignment(BaseContract):
    trial_member_id: UUID
    trial_id: UUID
    trial_name: str
    role_id: UUID
    role_name: str
    permission_level: str
    is_active: bool = True
