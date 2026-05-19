"""
Archive routes — folders & saved responses
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.archive import (
    ArchiveFolderCreate,
    ArchiveFolderResponse,
    SavedResponseCreate,
    SavedResponseUpdate,
    SavedResponseResponse,
)
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.archive_folder import ArchiveFolder
from app.models.saved_response import SavedResponse


from app.models.members import Member

router = APIRouter()

# ---------------------
# FOLDER ENDPOINTS
# ---------------------


@router.get("/folders/", response_model=List[ArchiveFolderResponse])
async def list_folders(
    org_id: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArchiveFolder)
        .where(ArchiveFolder.org_id == org_id)
        .where(ArchiveFolder.deleted_at.is_(None))
        .order_by(ArchiveFolder.created_at.desc())
    )
    folders = result.scalars().all()
    return folders


@router.post("/folders/", response_model=ArchiveFolderResponse, status_code=201)
async def create_folder(
    payload: ArchiveFolderCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    folder = ArchiveFolder(
        org_id=payload.org_id,
        trial_id=payload.trial_id,
        name=payload.name,
        user_id=member.id,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    folder = (
        (await db.execute(select(ArchiveFolder).where(ArchiveFolder.id == folder_id)))
        .scalars()
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    folder.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


# ---------------------
# SAVED RESPONSE ENDPOINTS
# ---------------------


@router.get("/responses/", response_model=List[SavedResponseResponse])
async def list_saved_responses(
    folder_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedResponse)
        .where(SavedResponse.folder_id == folder_id)
        .where(SavedResponse.deleted_at.is_(None))
        .order_by(SavedResponse.created_at.desc())
    )
    responses = result.scalars().all()
    return responses


@router.post("/responses/", response_model=SavedResponseResponse, status_code=201)
async def create_saved_response(
    payload: SavedResponseCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    saved_response = SavedResponse(
        folder_id=payload.folder_id,
        user_id=member.id,
        trial_id=payload.trial_id,
        org_id=payload.org_id,
        title=payload.title,
        question=payload.question,
        answer=payload.answer,
        raw_data=payload.raw_data,
        document_id=payload.document_id,
    )
    db.add(saved_response)
    await db.commit()
    await db.refresh(saved_response)
    return saved_response


@router.put("/responses/{response_id}", response_model=SavedResponseResponse)
async def update_saved_response(
    response_id: UUID,
    payload: SavedResponseUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    response = (
        (await db.execute(select(SavedResponse).where(SavedResponse.id == response_id)))
        .scalars()
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Saved response not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(response, field, value)

    await db.commit()
    await db.refresh(response)
    return response


@router.delete("/responses/{response_id}", status_code=204)
async def delete_saved_response(
    response_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    response = (
        (await db.execute(select(SavedResponse).where(SavedResponse.id == response_id)))
        .scalars()
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Saved response not found")
    response.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
