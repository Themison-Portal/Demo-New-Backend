"""
Patient visit routes — GET /, POST /
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.patient_visit import PatientVisitCreate, PatientVisitResponse
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.patient_visits import PatientVisit
from app.models.trial_patients import TrialPatient

router = APIRouter()


@router.get("/", response_model=List[PatientVisitResponse])
async def list_visits(
    patient_id: Optional[UUID] = None,
    trial_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PatientVisit, Member)
        .outerjoin(Member, PatientVisit.doctor_id == Member.id)
    )
    if patient_id:
        stmt = stmt.where(PatientVisit.patient_id == patient_id)
    if trial_id:
        stmt = stmt.where(PatientVisit.trial_id == trial_id)
    stmt = stmt.order_by(PatientVisit.visit_date.desc())

    result = await db.execute(stmt)
    rows = result.all()
    return [
        PatientVisitResponse(
            id=v.id,
            patient_id=v.patient_id,
            trial_id=v.trial_id,
            doctor_id=v.doctor_id,
            visit_date=v.visit_date,
            visit_time=v.visit_time,
            visit_type=v.visit_type,
            status=v.status,
            duration_minutes=v.duration_minutes,
            visit_number=v.visit_number,
            notes=v.notes,
            next_visit_date=v.next_visit_date,
            location=v.location,
            actual_date=v.actual_date,
            created_at=v.created_at,
            updated_at=v.updated_at,
            created_by=v.created_by,
            cost_data=v.cost_data,
            doctor_name=doc.name if doc else None,
        )
        for v, doc in rows
    ]


@router.post("/", response_model=PatientVisitResponse, status_code=201)
async def create_visit(
    payload: PatientVisitCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    # Validate patient is enrolled in trial
    enrollment = (await db.execute(
        select(TrialPatient).where(
            TrialPatient.patient_id == payload.patient_id,
            TrialPatient.trial_id == payload.trial_id,
        )
    )).scalars().first()

    if not enrollment:
        raise HTTPException(
            status_code=400,
            detail="Patient is not enrolled in this trial",
        )

    data = payload.model_dump()
    data["created_by"] = member.id
    visit = PatientVisit(**data)
    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    doc = (await db.execute(select(Member).where(Member.id == visit.doctor_id))).scalars().first()

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
        doctor_name=doc.name if doc else None,
    )
