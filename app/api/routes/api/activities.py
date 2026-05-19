from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.models.activity_types import ActivityType
from app.models.trial_activity_types import TrialActivityType
from app.contracts.activity_type import TrialActivityTypeResponse, TrialActivityTypeCreate
from app.dependencies.db import get_db
from app.dependencies.trial_access import get_trial_with_access
from app.models.trials import Trial

router = APIRouter()


@router.get("/", response_model=List[TrialActivityTypeResponse])
async def list_trial_activities(
    trial_id: UUID,
    trial: Trial = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialActivityType).where(TrialActivityType.trial_id == trial_id)
    )
    return result.scalars().all()


@router.get("/{activity_id}", response_model=TrialActivityTypeResponse)
async def get_trial_activity(
    trial_id: UUID,
    activity_id: str,
    trial: Trial = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialActivityType).where(
            TrialActivityType.trial_id == trial_id,
            TrialActivityType.activity_id == activity_id,
        )
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/", response_model=TrialActivityTypeResponse, status_code=201)
async def create_trial_activity(
    trial_id: UUID,
    payload: TrialActivityTypeCreate,
    trial: Trial = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    activity = TrialActivityType(id=uuid.uuid4(), trial_id=trial_id, **payload.model_dump())
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


@router.put("/{activity_id}", response_model=TrialActivityTypeResponse)
async def update_trial_activity(
    trial_id: UUID,
    activity_id: str,
    payload: TrialActivityTypeCreate,
    trial: Trial = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialActivityType).where(
            TrialActivityType.trial_id == trial_id,
            TrialActivityType.activity_id == activity_id,
        )
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(activity, k, v)
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=204)
async def delete_trial_activity(
    trial_id: UUID,
    activity_id: str,
    trial: Trial = Depends(get_trial_with_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialActivityType).where(
            TrialActivityType.trial_id == trial_id,
            TrialActivityType.activity_id == activity_id,
        )
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    await db.delete(activity)
    await db.commit()
    return
