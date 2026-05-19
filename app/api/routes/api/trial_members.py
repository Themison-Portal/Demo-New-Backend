"""
Trial member routes — GET /team/{trial_id}, GET /pending/{trial_id}, POST /, POST /pending
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.trial_member import (
    PendingMemberCreate,
    PendingMemberResponse,
    TrialMemberCreate,
    TrialMemberResponse,
)
from app.dependencies.auth import get_current_member
from app.dependencies.trial_access import get_trial_with_access
from app.dependencies.db import get_db
from app.models.invitations import Invitation
from app.models.members import Member
from app.models.profiles import Profile
from app.models.roles import Role
from app.models.trial_members import TrialMember
from app.models.trial_members_pending import TrialMemberPending

router = APIRouter()


@router.get("/team/{trial_id}", response_model=List[TrialMemberResponse])
async def get_trial_team(
    trial_id: UUID,
    member: Member = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialMember, Member, Role, Profile)
        .join(Member, TrialMember.member_id == Member.id)
        .join(Role, TrialMember.role_id == Role.id)
        .outerjoin(Profile, Member.profile_id == Profile.id)
        .where(TrialMember.trial_id == trial_id)
    )
    rows = result.all()
    return [
        TrialMemberResponse(
            id=tm.id,
            trial_id=tm.trial_id,
            member_id=tm.member_id,
            role_id=tm.role_id,
            start_date=tm.start_date,
            end_date=tm.end_date,
            is_active=tm.is_active,
            created_at=tm.created_at,
            member_name=m.name,
            member_email=m.email,
            role_name=r.name,
            permission_level=r.permission_level,
            first_name=p.first_name if p else None,
            last_name=p.last_name if p else None,
        )
        for tm, m, r, p in rows
    ]


@router.get("/pending/{trial_id}", response_model=List[PendingMemberResponse])
async def get_pending_members(
    trial_id: UUID,
    member: Member = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialMemberPending, Invitation, Role)
        .join(Invitation, TrialMemberPending.invitation_id == Invitation.id)
        .join(Role, TrialMemberPending.role_id == Role.id)
        .where(TrialMemberPending.trial_id == trial_id)
    )
    rows = result.all()
    return [
        PendingMemberResponse(
            id=tmp.id,
            trial_id=tmp.trial_id,
            invitation_id=tmp.invitation_id,
            role_id=tmp.role_id,
            invited_by=tmp.invited_by,
            created_at=tmp.created_at,
            notes=tmp.notes,
            invitation_email=inv.email,
            invitation_name=inv.name,
            invitation_status=inv.status,
            role_name=r.name,
            permission_level=r.permission_level,
        )
        for tmp, inv, r in rows
    ]


@router.post("/", response_model=TrialMemberResponse, status_code=201)
async def add_trial_member(
    payload: TrialMemberCreate,
    trial=Depends(get_trial_with_access),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if member.default_role not in ["superadmin", "admin", "staff"]:
        raise HTTPException(status_code=403, detail="Only admins can add trial members")
    data = payload.model_dump()
    data["trial_id"] = trial.id
    tm = TrialMember(**data)
    db.add(tm)
    await db.commit()
    await db.refresh(tm)

    m = (
        (await db.execute(select(Member).where(Member.id == tm.member_id)))
        .scalars()
        .first()
    )
    r = (await db.execute(select(Role).where(Role.id == tm.role_id))).scalars().first()

    return TrialMemberResponse(
        id=tm.id,
        trial_id=tm.trial_id,
        member_id=tm.member_id,
        role_id=tm.role_id,
        start_date=tm.start_date,
        end_date=tm.end_date,
        is_active=tm.is_active,
        created_at=tm.created_at,
        member_name=m.name if m else None,
        member_email=m.email if m else None,
        role_name=r.name if r else None,
        permission_level=r.permission_level if r else None,
    )


@router.post("/pending", response_model=PendingMemberResponse, status_code=201)
async def add_pending_member(
    payload: PendingMemberCreate,
    trial=Depends(get_trial_with_access),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    data["invited_by"] = member.id
    data["trial_id"] = trial.id
    tmp = TrialMemberPending(**data)
    db.add(tmp)
    await db.commit()
    await db.refresh(tmp)

    inv = (
        (await db.execute(select(Invitation).where(Invitation.id == tmp.invitation_id)))
        .scalars()
        .first()
    )
    r = (await db.execute(select(Role).where(Role.id == tmp.role_id))).scalars().first()

    return PendingMemberResponse(
        id=tmp.id,
        trial_id=tmp.trial_id,
        invitation_id=tmp.invitation_id,
        role_id=tmp.role_id,
        invited_by=tmp.invited_by,
        created_at=tmp.created_at,
        notes=tmp.notes,
        invitation_email=inv.email if inv else None,
        invitation_name=inv.name if inv else None,
        invitation_status=inv.status if inv else None,
        role_name=r.name if r else None,
        permission_level=r.permission_level if r else None,
    )


@router.patch("/{member_id}")
async def update_trial_member(
    member_id: UUID,
    payload: dict,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm.attributes import flag_modified

    tm = (
        (await db.execute(select(TrialMember).where(TrialMember.id == member_id)))
        .scalars()
        .first()
    )
    if not tm:
        raise HTTPException(status_code=404, detail="Trial member not found")

    for key, value in payload.items():
        if hasattr(tm, key):
            if key == "settings" and isinstance(value, dict):
                # Merge with existing settings instead of replacing
                current = tm.settings or {}
                tm.settings = {**current, **value}
                flag_modified(tm, "settings")
            else:
                setattr(tm, key, value)

    await db.commit()
    await db.refresh(tm)

    m = (
        (await db.execute(select(Member).where(Member.id == tm.member_id)))
        .scalars()
        .first()
    )
    r = (await db.execute(select(Role).where(Role.id == tm.role_id))).scalars().first()
    p = (
        (await db.execute(select(Profile).where(Profile.id == m.profile_id)))
        .scalars()
        .first()
        if m
        else None
    )
    return TrialMemberResponse(
        id=tm.id,
        trial_id=tm.trial_id,
        member_id=tm.member_id,
        role_id=tm.role_id,
        start_date=tm.start_date,
        end_date=tm.end_date,
        is_active=tm.is_active,
        created_at=tm.created_at,
        member_name=m.name if m else None,
        member_email=m.email if m else None,
        role_name=r.name if r else None,
        permission_level=r.permission_level if r else None,
        first_name=p.first_name if p else None,
        last_name=p.last_name if p else None,
        settings=tm.settings,
    )


@router.delete("/{member_id}", status_code=204)
async def remove_trial_member(
    member_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    tm = (
        (await db.execute(select(TrialMember).where(TrialMember.id == member_id)))
        .scalars()
        .first()
    )
    if not tm:
        raise HTTPException(status_code=404, detail="Trial member not found")
    if member.default_role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(tm)
    await db.commit()
