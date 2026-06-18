"""
Trial document routes — GET /, GET /{id}, POST /upload, PUT /{id}, DELETE /{id}
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import LargeBinary, bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contracts.document import DocumentResponse, DocumentUpdate
from app.contracts.storage import DocumentDownloadUrlResponse
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.dependencies.storage import get_storage_service
from app.dependencies.trial_access import get_trial_with_access
from app.models.documents import Document
from app.models.members import Member
from app.models.trials import Trial
from app.services.crud import CRUDBase
from app.services.storage.base import StorageService

logger = logging.getLogger(__name__)

router = APIRouter()


DOWNLOAD_URL_TTL_HOURS = 1
DOWNLOAD_URL_TTL_SECONDS = DOWNLOAD_URL_TTL_HOURS * 3600


async def _uploader_names(docs: List[Document], db: AsyncSession) -> Dict[UUID, str]:
    """Batch-resolve `uploaded_by` (member id) → member display name."""
    ids = {d.uploaded_by for d in docs if d.uploaded_by is not None}
    if not ids:
        return {}
    rows = (
        await db.execute(select(Member.id, Member.name).where(Member.id.in_(ids)))
    ).all()
    return {mid: name for mid, name in rows}


def _to_response(doc: Document, names: Dict[UUID, str]) -> DocumentResponse:
    resp = DocumentResponse.model_validate(doc)
    resp.uploaded_by_name = names.get(doc.uploaded_by)
    return resp


@router.get("/", response_model=List[DocumentResponse])
async def list_trial_documents(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    List documents for a trial. Returns metadata only (plus a derived
    `uploaded_by_name`). `document_url` is the raw GCS blob path; the FE must
    call `GET /{document_id}/download-url` to obtain a signed HTTPS URL when it
    needs to actually open/download the file.

    Authorization: caller must be a member of the trial's organization
    (admins) or a TrialMember of this trial — enforced by
    `get_trial_with_access`.
    """
    await get_trial_with_access(trial_id, member, db)
    crud = CRUDBase(Document, db)
    docs = await crud.get_multi(filters={"trial_id": trial_id})
    names = await _uploader_names(docs, db)
    return [_to_response(d, names) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_trial_document(
    document_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single document's metadata. `document_url` is a raw GCS blob path —
    use `GET /{document_id}/download-url` for an HTTPS URL.

    Authorization: same trial-access rules as the list endpoint.
    """
    crud = CRUDBase(Document, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # 404 on cross-org access too — don't leak existence
    await get_trial_with_access(doc.trial_id, member, db)
    names = await _uploader_names([doc], db)
    return _to_response(doc, names)


@router.get(
    "/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
)
async def get_document_download_url(
    document_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """
    Return a fresh, short-lived HTTPS URL the FE can pass to a PDF viewer.

    Sign-on-demand keeps the leak window short (1h) and avoids re-signing every
    document on every list call. The FE should call this endpoint immediately
    before opening the viewer; if the viewer stays open longer than 1h and the
    URL 401/403s, refetch.

    Authorization: caller must have access to the document's parent trial
    (`get_trial_with_access`). Without this check the endpoint would mint
    download links for any document UUID across the whole tenant.
    """
    crud = CRUDBase(Document, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.document_url:
        raise HTTPException(status_code=404, detail="Document has no file attached")

    # Enforce trial-access (raises 403/404 on no access — don't sign anything yet)
    await get_trial_with_access(doc.trial_id, member, db)

    if doc.document_url.startswith(("http://", "https://")):
        # Already an absolute URL (e.g., LocalStorageService in dev)
        url = doc.document_url
    else:
        try:
            url = storage.get_signed_url(
                get_settings().gcs_bucket_trial_documents,
                doc.document_url,
                expiration_hours=DOWNLOAD_URL_TTL_HOURS,
            )
        except Exception as e:
            logger.exception(f"Failed to sign URL for document {document_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate download URL")

    return DocumentDownloadUrlResponse(
        url=url,
        expires_in_seconds=DOWNLOAD_URL_TTL_SECONDS,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_trial_document(
    file: UploadFile = File(...),
    trial_id: UUID = Form(...),
    document_name: str = Form(...),
    document_type: str = Form("other"),
    description: str = Form(""),
    category: Optional[str] = Form(None),
    document_version: Optional[str] = Form(None),
    amendment_version: Optional[str] = Form(None),
    release_date: Optional[str] = Form(None),
    is_current: bool = Form(False),
    source_type: Optional[str] = Form(None),
    source_reference: Optional[str] = Form(None),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    crud_trial = CRUDBase(Trial, db)
    trial = await crud_trial.get(trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    settings = get_settings()
    bucket = settings.gcs_bucket_trial_documents

    import uuid
    file_data = await file.read()
    folder = f"trials/{trial_id}"
    # Ensure a unique filename to avoid duplicate URL constraint
    unique_suffix = uuid.uuid4().hex[:8]
    base_name = file.filename or "document"
    # Preserve extension if present
    if "." in base_name:
        name_part, ext = base_name.rsplit(".", 1)
        unique_filename = f"{name_part}_{unique_suffix}.{ext}"
    else:
        unique_filename = f"{base_name}_{unique_suffix}"
    upload_result = storage.upload_file(
        bucket_name=bucket,
        file_data=file_data,
        filename=unique_filename,
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )

    # Durable fallback: also store the bytes in Postgres so the PDF survives the
    # ephemeral /app/uploads disk being wiped on redeploy. Keyed by the same
    # relative path the /local-files URL resolves to; served by the /local-files
    # route when the on-disk copy is gone.
    rel_path = f"{folder}/{unique_filename}"
    await db.execute(
        text(
            "INSERT INTO document_blobs (rel_path, content, content_type) "
            "VALUES (:rel_path, :content, :content_type) "
            "ON CONFLICT (rel_path) DO UPDATE SET "
            "content = EXCLUDED.content, content_type = EXCLUDED.content_type"
        ).bindparams(bindparam("content", type_=LargeBinary)),
        {
            "rel_path": rel_path,
            "content": file_data,
            "content_type": file.content_type or "application/pdf",
        },
    )

    # Category defaults to the document_type when the FE omits it.
    resolved_category = category or document_type

    # "Only one current" invariant: when this upload is the current protocol,
    # clear is_current on the trial's sibling protocol-category documents so the
    # BE remains the single source of truth for that flag.
    if is_current and resolved_category and resolved_category.lower() == "protocol":
        await db.execute(
            text(
                "UPDATE trial_documents SET is_current = false "
                "WHERE trial_id = :trial_id AND lower(category) = 'protocol'"
            ),
            {"trial_id": trial_id},
        )

    doc = Document(
        document_name=document_name,
        document_type=document_type,
        document_url=upload_result["path"],
        trial_id=trial_id,
        uploaded_by=member.id,
        status="active",
        file_size=upload_result["file_size"],
        mime_type=file.content_type,
        description=description,
        category=resolved_category,
        document_version=document_version,
        amendment_version=amendment_version,
        release_date=release_date,
        is_current=is_current,
        source_type=source_type,
        source_reference=source_reference,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    names = await _uploader_names([doc], db)
    return _to_response(doc, names)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_trial_document(
    document_id: UUID,
    payload: DocumentUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(Document, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fields = payload.model_dump(exclude_unset=True)

    # "Only one current" invariant — clear is_current on sibling protocol-category
    # docs of the same trial when this one is being marked current.
    if fields.get("is_current") and doc.trial_id is not None:
        await db.execute(
            text(
                "UPDATE trial_documents SET is_current = false "
                "WHERE trial_id = :trial_id AND lower(category) = 'protocol' "
                "AND id <> :doc_id"
            ),
            {"trial_id": doc.trial_id, "doc_id": document_id},
        )

    updated = await crud.update(document_id, fields)
    names = await _uploader_names([updated], db)
    return _to_response(updated, names)


@router.delete("/{document_id}", status_code=204)
async def delete_trial_document(
    document_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    crud = CRUDBase(Document, db)
    doc = await crud.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from storage
    settings = get_settings()
    if doc.document_url:
        storage.delete_file(settings.gcs_bucket_trial_documents, doc.document_url)

    await crud.delete(document_id)
