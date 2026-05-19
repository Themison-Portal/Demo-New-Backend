"""
Member routes — GET /me, GET /me/trial-assignments, GET /, PUT /{id}, DELETE /{id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.member import MemberResponse, MemberTrialAssignment, MemberUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile
from app.models.roles import Role
from app.models.trial_members import TrialMember
from app.models.trials import Trial
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/me", response_model=MemberResponse)
async def get_current_member_info(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(
        select(Profile).where(Profile.id == member.profile_id)
    )).scalars().first()

    return MemberResponse(
        id=member.id,
        name=member.name,
        email=member.email,
        default_role=member.default_role,
        onboarding_completed=member.onboarding_completed,
        organization_id=member.organization_id,
        profile_id=member.profile_id,
        invited_by=member.invited_by,
        created_at=member.created_at,
        updated_at=member.updated_at,
        first_name=profile.first_name if profile else None,
        last_name=profile.last_name if profile else None,
    )


@router.get("/me/trial-assignments", response_model=List[MemberTrialAssignment])
async def get_my_trial_assignments(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialMember, Trial, Role)
        .join(Trial, TrialMember.trial_id == Trial.id)
        .join(Role, TrialMember.role_id == Role.id)
        .where(TrialMember.member_id == member.id)
    )
    rows = result.all()
    return [
        MemberTrialAssignment(
            trial_member_id=tm.id,
            trial_id=trial.id,
            trial_name=trial.name,
            role_id=role.id,
            role_name=role.name,
            permission_level=role.permission_level,
            is_active=tm.is_active,
        )
        for tm, trial, role in rows
    ]


@router.get("/", response_model=List[MemberResponse])
async def list_members(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Member, db)
    members = await crud.get_multi(filters={"organization_id": member.organization_id})
    return members


@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Member, db)
    target = await crud.get(member_id)
    if not target or target.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Member not found")

    updated = await crud.update(member_id, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Member, db)
    target = await crud.get(member_id)
    if not target or target.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Member not found")

    await crud.delete(member_id)
