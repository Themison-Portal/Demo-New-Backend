"""
Patient visit - complete visit endpoint
POST: /trials/{trial_id}/patients/{patient_id}/visits/{visit_id}/complete
"""

from datetime import datetime, date, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.contracts.patient_visit import PatientVisitResponse
from app.models.members import Member
from app.models.patient_visits import PatientVisit
from app.models.visit_activities import VisitActivity
from app.utils.permissions import is_critical_trial_role  # PI/CRC roles checker

router = APIRouter()


@router.post(
    "/trials/{trial_id}/patients/{patient_id}/visits/{visit_id}/complete",
    response_model=PatientVisitResponse,
)
async def complete_visit(
    trial_id: str,
    patient_id: str,
    visit_id: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete a patient visit
    - Only PI/CRC can complete
    - All activities must be completed or not_applicable
    """
    from app.models.trial_members import TrialMember
    from app.models.roles import Role

    # Check permission
    role_stmt = (
        select(Role.name)
        .join(TrialMember, TrialMember.role_id == Role.id)
        .where(
            TrialMember.member_id == member.id,
            TrialMember.trial_id == trial_id
        )
    )
    role_result = await db.execute(role_stmt)
    trial_role = role_result.scalars().first()

    if not is_critical_trial_role(trial_role):
        raise HTTPException(
            status_code=403, detail="Only PI and CRC can complete visits"
        )

    # Fetch visit
    visit_stmt = select(PatientVisit).where(
        PatientVisit.id == visit_id,
        PatientVisit.patient_id == patient_id,
        PatientVisit.trial_id == trial_id,
    )
    visit_result = await db.execute(visit_stmt)
    visit: PatientVisit = visit_result.scalars().first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if visit.status == "completed":
        raise HTTPException(status_code=400, detail="Visit is already completed")

    # Fetch all activities for this visit
    activities_stmt = select(VisitActivity).where(VisitActivity.visit_id == visit_id)
    activities_result = await db.execute(activities_stmt)
    activities: List[VisitActivity] = activities_result.scalars().all()

    # Check pending activities
    pending_activities = [a.activity_name for a in activities if a.status == "pending"]
    if pending_activities:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete visit with pending activities: {pending_activities}",
        )

    # Complete the visit
    visit.status = "completed"
    visit.actual_date = date.today()
    visit.updated_at = datetime.now(timezone.utc)

    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    # Fetch doctor for response
    doctor = (await db.execute(select(Member).where(Member.id == visit.doctor_id))).scalars().first()

    return PatientVisitResponse(
        id=visit.id,
        patient_id=visit.patient_id,
        trial_id=visit.trial_id,
        doctor_id=visit.doctor_id,
        visit_date=visit.visit_date,
        visit_time=visit.visit_time,
        visit_type=visit.visit_type,
        status=visit.status,
        duration_minutes=visit.duration_minutes,
        visit_number=visit.visit_number,
        notes=visit.notes,
        next_visit_date=visit.next_visit_date,
        location=visit.location,
        actual_date=visit.actual_date,
        created_at=visit.created_at,
        updated_at=visit.updated_at,
        created_by=visit.created_by,
        cost_data=visit.cost_data,
        doctor_name=doctor.name if doctor else None,
    )
