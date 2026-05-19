"""
Trial patient routes — GET /, POST /, PUT /{id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.trial_patient import TrialPatientCreate, TrialPatientResponse, TrialPatientUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.patients import Patient
from app.models.trial_patients import TrialPatient
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/", response_model=List[TrialPatientResponse])
async def list_trial_patients(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialPatient, Patient)
        .join(Patient, TrialPatient.patient_id == Patient.id)
        .where(TrialPatient.trial_id == trial_id)
        .order_by(TrialPatient.created_at.desc())
    )
    rows = result.all()
    return [
        TrialPatientResponse(
            id=tp.id,
            trial_id=tp.trial_id,
            patient_id=tp.patient_id,
            enrollment_date=tp.enrollment_date,
            status=tp.status,
            randomization_code=tp.randomization_code,
            notes=tp.notes,
            created_at=tp.created_at,
            updated_at=tp.updated_at,
            assigned_by=tp.assigned_by,
            cost_data=tp.cost_data,
            patient_data=tp.patient_data,
            patient_code=p.patient_code,
            patient_first_name=p.first_name,
            patient_last_name=p.last_name,
        )
        for tp, p in rows
    ]


@router.post("/", response_model=TrialPatientResponse, status_code=201)
async def enroll_patient(
    payload: TrialPatientCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    data["assigned_by"] = member.id
    tp = TrialPatient(**data)
    db.add(tp)
    await db.commit()
    await db.refresh(tp)

    patient = (await db.execute(select(Patient).where(Patient.id == tp.patient_id))).scalars().first()
    return TrialPatientResponse(
        id=tp.id,
        trial_id=tp.trial_id,
        patient_id=tp.patient_id,
        enrollment_date=tp.enrollment_date,
        status=tp.status,
        randomization_code=tp.randomization_code,
        notes=tp.notes,
        created_at=tp.created_at,
        updated_at=tp.updated_at,
        assigned_by=tp.assigned_by,
        cost_data=tp.cost_data,
        patient_data=tp.patient_data,
        patient_code=patient.patient_code if patient else None,
        patient_first_name=patient.first_name if patient else None,
        patient_last_name=patient.last_name if patient else None,
    )


@router.put("/{enrollment_id}", response_model=TrialPatientResponse)
async def update_enrollment(
    enrollment_id: UUID,
    payload: TrialPatientUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(TrialPatient, db)
    tp = await crud.get(enrollment_id)
    if not tp:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    updated = await crud.update(enrollment_id, payload.model_dump(exclude_unset=True))
    return updated
