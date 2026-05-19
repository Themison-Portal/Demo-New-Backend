"""
Contracts for roles.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class RoleBase(BaseContract):
    name: str
    description: Optional[str] = None
    permission_level: str = "read"


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase, TimestampedContract):
    id: UUID
    organization_id: UUID
    created_by: Optional[UUID] = None
