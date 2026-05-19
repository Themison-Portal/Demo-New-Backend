"""
Contracts for invitations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .base import BaseContract


class InvitationBase(BaseContract):
    email: str
    name: Optional[str] = None
    org_role: str


class InvitationResponse(InvitationBase):
    id: UUID
    organization_id: UUID
    status: Optional[str] = "pending"
    invited_by: Optional[UUID] = None
    invited_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None


class InvitationBatchItem(BaseContract):
    email: str
    name: Optional[str] = None
    org_role: str


class InvitationBatchCreate(BaseContract):
    invitations: List[InvitationBatchItem]


class InvitationCountResponse(BaseContract):
    pending: int = 0
    accepted: int = 0
    expired: int = 0
    total: int = 0
