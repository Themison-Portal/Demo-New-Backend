from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.trials import Trial
from app.models.trial_members import TrialMember
from app.models.members import Member

ADMIN_ROLES = {"superadmin", "admin", "staff"}


async def get_trial_with_access(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> Trial:

    # Fetch trial
    trial = (
        (await db.execute(select(Trial).where(Trial.id == trial_id))).scalars().first()
    )

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Org isolation check
    if trial.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Admin check
    if member.default_role in ADMIN_ROLES:
        return trial

    # Trial membership check
    trial_member = (
        (
            await db.execute(
                select(TrialMember).where(
                    TrialMember.trial_id == trial_id,
                    TrialMember.member_id == member.id,
                    TrialMember.is_active == True,
                )
            )
        )
        .scalars()
        .first()
    )

    if not trial_member:
        raise HTTPException(status_code=403, detail="Not authorized for this trial")

    return trial
