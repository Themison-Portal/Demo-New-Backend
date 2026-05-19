"""
Patient routes — GET /, GET /{id}, POST /, PUT /{id}, DELETE /{id}, GET /generate-code
"""

import random
import string
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.patient import PatientCreate, PatientResponse, PatientUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.patients import Patient
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/generate-code")
async def generate_patient_code(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Generate a unique patient code in format PAT-XXXXX."""
    while True:
        suffix = "".join(random.choices(string.digits, k=5))
        code = f"PAT-{suffix}"
        existing = (await db.execute(
            select(func.count()).select_from(Patient).where(Patient.patient_code == code)
        )).scalar_one()
        if existing == 0:
            return {"patient_code": code}


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Patient, db)
    return await crud.get_multi(filters={"organization_id": member.organization_id})


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Patient, db)
    patient = await crud.get(patient_id)
    if not patient or patient.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    payload: PatientCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Patient, db)
    data = payload.model_dump()
    data["organization_id"] = member.organization_id
    return await crud.create(data)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Patient, db)
    patient = await crud.get(patient_id)
    if not patient or patient.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return await crud.update(patient_id, payload.model_dump(exclude_unset=True))


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete — sets is_active=False."""
    crud = CRUDBase(Patient, db)
    patient = await crud.get(patient_id)
    if not patient or patient.organization_id != member.organization_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    await crud.update(patient_id, {"is_active": False})
