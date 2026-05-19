"""
Visit activity routes — GET /, PATCH /{activity_id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.visit_activity import VisitActivityResponse, VisitActivityUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.visit_activities import VisitActivity

router = APIRouter()


@router.get("/{visit_id}/activities", response_model=List[VisitActivityResponse])
async def list_visit_activities(
    visit_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VisitActivity).where(VisitActivity.visit_id == visit_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/activities/{activity_id}", response_model=VisitActivityResponse)
async def update_visit_activity(
    activity_id: UUID,
    payload: VisitActivityUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VisitActivity).where(VisitActivity.id == activity_id)
    result = await db.execute(stmt)
    activity = result.scalars().first()

    if not activity:
        raise HTTPException(status_code=404, detail="Visit activity not found")

    activity.status = payload.status
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity
