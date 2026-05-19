"""
Storage routes — upload, download, delete files via GCS.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import get_settings
from app.contracts.storage import UploadResponse
from app.dependencies.auth import get_current_member
from app.dependencies.storage import get_storage_service
from app.models.members import Member
from app.services.storage.base import StorageService

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    bucket: str | None = None,
    folder: str | None = None,
    member: Member = Depends(get_current_member),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload a file to GCS and return its path + signed URL."""
    settings = get_settings()
    bucket_name = bucket or settings.gcs_bucket_trial_documents

    if not bucket_name:
        raise HTTPException(status_code=500, detail="No GCS bucket configured")

    data = await file.read()
    result = storage.upload_file(
        bucket_name=bucket_name,
        file_data=data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )
    return result


# Removed: GET /storage/download/{document_id} stub — superseded by
# GET /api/trial-documents/{document_id}/download-url (with trial-access auth).


@router.delete("/{path:path}", status_code=204)
async def delete_file(
    path: str,
    bucket: str | None = None,
    member: Member = Depends(get_current_member),
    storage: StorageService = Depends(get_storage_service),
):
    """Delete a file from GCS by its blob path."""
    settings = get_settings()
    bucket_name = bucket or settings.gcs_bucket_trial_documents

    if not bucket_name:
        raise HTTPException(status_code=500, detail="No GCS bucket configured")

    storage.delete_file(bucket_name, path)
