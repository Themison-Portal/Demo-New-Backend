"""
Trial routes — GET /, GET /{id}, POST /with-assignments, PUT /{id}
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.contracts.trial_template import VisitScheduleTemplate
from datetime import datetime, timezone

from app.contracts.trial import TrialResponse, TrialUpdate, TrialWithAssignmentsCreate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.trial_members import TrialMember
from app.models.trial_members_pending import TrialMemberPending
from app.models.activity_types import ActivityType
from app.models.trial_activity_types import TrialActivityType
from app.models.trials import Trial
from app.models.documents import Document
from app.services.crud import CRUDBase
from app.dependencies.trial_access import get_trial_with_access

router = APIRouter()


@router.get("/", response_model=List[TrialResponse])
async def list_trials(
    demo_mode: Optional[str] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    # When the FE passes a demo_mode, scope to that dataset (sample/full/building);
    # otherwise return all trials for the org.
    filters = {"organization_id": member.organization_id}
    if demo_mode is not None:
        filters["demo_mode"] = demo_mode
    crud = CRUDBase(Trial, db)
    return await crud.get_multi(filters=filters, limit=1000)


@router.get("/by-slug", response_model=TrialResponse)
async def get_trial_by_slug(
    slug: str,
    demo_mode: Optional[str] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Resolve the FE's bare slug (+ demo_mode) to the BE trial. Defined BEFORE
    the `/{trial_id}` route so 'by-slug' isn't parsed as a UUID."""
    stmt = select(Trial).where(
        Trial.organization_id == member.organization_id,
        Trial.slug == slug,
    )
    if demo_mode is not None:
        stmt = stmt.where(Trial.demo_mode == demo_mode)
    trial = (await db.execute(stmt)).scalars().first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@router.get("/{trial_id}", response_model=TrialResponse)
async def get_trial(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Trial, db)
    trial = await crud.get(trial_id)
    if not trial or trial.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@router.post("/with-assignments", response_model=TrialResponse, status_code=201)
async def create_trial_with_assignments(
    payload: TrialWithAssignmentsCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    # Create trial
    trial_data = payload.model_dump(exclude={"members", "pending_members"})
    trial_data["organization_id"] = member.organization_id
    trial_data["created_by"] = member.id

    trial = Trial(**trial_data)
    db.add(trial)
    await db.flush()  # get trial.id

    # Create trial_members
    for assignment in payload.members:
        db.add(
            TrialMember(
                trial_id=trial.id,
                member_id=assignment.member_id,
                role_id=assignment.role_id,
            )
        )

    # Create trial_members_pending
    for pending in payload.pending_members:
        db.add(
            TrialMemberPending(
                trial_id=trial.id,
                invitation_id=pending.invitation_id,
                role_id=pending.role_id,
                invited_by=member.id,
            )
        )

    await db.commit()
    await db.refresh(trial)
    return trial


@router.put("/{trial_id}", response_model=TrialResponse)
async def update_trial(
    trial_id: UUID,
    payload: TrialUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Trial, db)
    trial = await crud.get(trial_id)
    if not trial or trial.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Trial not found")

    updated = await crud.update(trial_id, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/{trial_id}", status_code=204)
async def delete_trial(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Trial, db)
    trial = await crud.get(trial_id)
    if not trial or trial.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Cascade BE-owned trial data. Documents are removed via the same ORM path
    # the single-document delete uses (so their docling chunks / chat links go
    # too); members are plain rows. FE-owned child data (scaffolds, maps, …) is
    # cascaded on the FE side.
    docs = (
        await db.execute(select(Document).where(Document.trial_id == trial_id))
    ).scalars().all()
    for doc in docs:
        await db.delete(doc)
    await db.execute(
        text("DELETE FROM trial_members WHERE trial_id = :t"), {"t": trial_id}
    )
    await db.execute(
        text("DELETE FROM trial_members_pending WHERE trial_id = :t"), {"t": trial_id}
    )
    await db.delete(trial)
    await db.commit()
    return None


@router.get("/{trial_id}/template", response_model=VisitScheduleTemplate)
async def get_visit_schedule_template(
    trial_id: UUID,
    trial: Trial = Depends(get_trial_with_access),  # ensures trial access
    db: AsyncSession = Depends(get_db),
):
    # Return template or empty default
    return trial.visit_schedule_template or VisitScheduleTemplate().dict()


@router.put("/{trial_id}/template", response_model=VisitScheduleTemplate)
async def update_visit_schedule_template(
    trial_id: UUID,
    body: VisitScheduleTemplate,
    trial: Trial = Depends(get_trial_with_access),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    # Only admins/superadmins can update
    if member.default_role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Only admins can update template")

    template = body.dict()

    # Validate exactly one day_zero
    day_zero_count = sum(1 for v in template["visits"] if v.get("is_day_zero"))
    if day_zero_count != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Template must have exactly one visit marked as day_zero, found {day_zero_count}",
        )

    # Optional: validate duplicate orders/names
    visit_orders = [v["order"] for v in template["visits"]]
    visit_names = [v["name"] for v in template["visits"]]
    if len(set(visit_orders)) != len(visit_orders):
        raise HTTPException(
            status_code=400, detail="Template has duplicate visit orders"
        )
    if len(set(visit_names)) != len(visit_names):
        raise HTTPException(
            status_code=400, detail="Template has duplicate visit names"
        )

    # ==========================================================
    # AUTO-CREATE MISSING ACTIVITIES LOGIC HERE
    # ==========================================================

    activity_ids = set()

    for visit in template["visits"]:
        for activity_id in visit.get("activity_ids", []):
            activity_ids.add(activity_id)

    for activity_id in activity_ids:

        # Check global activity_types
        global_result = await db.execute(
            select(ActivityType).where(ActivityType.id == activity_id)
        )
        global_activity = global_result.scalars().first()

        if global_activity:
            continue

        # Check trial_activity_types
        trial_result = await db.execute(
            select(TrialActivityType).where(
                TrialActivityType.trial_id == trial_id,
                TrialActivityType.activity_id == activity_id,
            )
        )
        trial_activity = trial_result.scalars().first()

        if trial_activity:
            continue

        # Create missing trial activity
        new_activity = TrialActivityType(
            trial_id=trial_id,
            activity_id=activity_id,
            name=activity_id.replace("_", " ").title(),
            category=None,
            description=None,
            is_custom=True,
        )

        db.add(new_activity)
    await db.flush()  # Ensure all new activities are saved before committing template
    # Save to DB
    trial.visit_schedule_template = template
    trial.updated_at = datetime.now(timezone.utc)
    db.add(trial)
    await db.commit()
    await db.refresh(trial)

    return trial.visit_schedule_template
