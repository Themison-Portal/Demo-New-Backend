from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.members import Member
from app.models.trial_members import TrialMember
from app.models.trials import Trial
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db

router = APIRouter()


@router.post("/{trial_id}/validate-access")
async def validate_trial_access_bulk(
    trial_id: str,
    user_ids: List[str],
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate which users have access to a trial.
    Admins have access to all trial users automatically.
    Trial members have access only if they are assigned.
    Returns lists: valid_user_ids, invalid_user_ids
    """

    # Fetch trial
    trial = (
        (await db.execute(select(Trial).where(Trial.id == trial_id))).scalars().first()
    )
    if not trial or trial.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Fetch members of trial
    result = await db.execute(
        select(TrialMember).where(
            TrialMember.trial_id == trial_id,
            TrialMember.member_id.in_(user_ids),
            TrialMember.is_active == True,
        )
    )
    trial_members = result.scalars().all()
    trial_member_ids = {tm.member_id for tm in trial_members}

    # Fetch org roles of requested users
    result = await db.execute(
        select(Member.id, Member.default_role).where(Member.id.in_(user_ids))
    )
    org_members = result.all()
    org_roles = {m.id: m.default_role for m in org_members}

    valid_user_ids = []
    invalid_user_ids = []

    for user_id in user_ids:
        role = org_roles.get(user_id)
        if role in ("superadmin", "admin") or user_id in trial_member_ids:
            valid_user_ids.append(user_id)
        else:
            invalid_user_ids.append(user_id)

    return {"valid_user_ids": valid_user_ids, "invalid_user_ids": invalid_user_ids}
