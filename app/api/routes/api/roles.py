"""
Role routes — GET /, POST /, DELETE /{id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.role import RoleCreate, RoleResponse
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.roles import Role
from app.models.trial_members import TrialMember
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Role, db)
    return await crud.get_multi(filters={"organization_id": member.organization_id})


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(
    payload: RoleCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Role, db)
    data = payload.model_dump()
    data["organization_id"] = member.organization_id
    data["created_by"] = member.id
    return await crud.create(data)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    # Verify role belongs to org
    crud = CRUDBase(Role, db)
    role = await crud.get(role_id)
    if not role or role.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check no active trial_members reference this role
    active_count = (await db.execute(
        select(func.count()).select_from(TrialMember).where(
            TrialMember.role_id == role_id, TrialMember.is_active == True
        )
    )).scalar_one()

    if active_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete role: {active_count} active trial members use it",
        )

    await crud.delete(role_id)
