"""
Patient document routes — GET /, POST /, PUT /{id}, DELETE /{id}
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contracts.patient_document import PatientDocumentResponse, PatientDocumentUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.dependencies.storage import get_storage_service
from app.models.members import Member
from app.models.patient_documents import PatientDocument
from app.services.crud import CRUDBase
from app.services.storage.base import StorageService

router = APIRouter()


@router.get("/", response_model=List[PatientDocumentResponse])
async def list_patient_documents(
    patient_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(PatientDocument, db)
    filters = {}
    if patient_id:
        filters["patient_id"] = patient_id
    return await crud.get_multi(filters=filters)


@router.post("/", response_model=PatientDocumentResponse, status_code=201)
async def upload_patient_document(
    file: UploadFile = File(...),
    patient_id: UUID = Form(...),
    document_name: str = Form(...),
    document_type: str = Form("other"),
    description: str = Form(""),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    settings = get_settings()
    bucket = settings.gcs_bucket_patient_documents

    file_data = await file.read()
    folder = f"patients/{patient_id}"

    upload_result = storage.upload_file(
        bucket_name=bucket,
        file_data=file_data,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )

    doc = PatientDocument(
        document_name=document_name,
        document_type=document_type,
        document_url=upload_result["path"],
        patient_id=patient_id,
        uploaded_by=member.id,
        status="active",
        file_size=upload_result["file_size"],
        mime_type=file.content_type,
        description=description,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.put("/{document_id}", response_model=PatientDocumentResponse)
async def update_patient_document(
    document_id: UUID,
    payload: PatientDocumentUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(PatientDocument, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return await crud.update(document_id, payload.model_dump(exclude_unset=True))


@router.delete("/{document_id}", status_code=204)
async def delete_patient_document(
    document_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    crud = CRUDBase(PatientDocument, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = get_settings()
    if doc.document_url:
        storage.delete_file(settings.gcs_bucket_patient_documents, doc.document_url)

    await crud.delete(document_id)
