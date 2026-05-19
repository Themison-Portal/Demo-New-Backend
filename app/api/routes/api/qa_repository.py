"""
QA repository routes — GET /, POST /, PUT /{id}/verify, DELETE /{id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.qa_repository import QAItemCreate, QAItemResponse, QAItemUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile
from app.models.qa_repository import QARepositoryItem
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/", response_model=List[QAItemResponse])
async def list_qa_items(
    trial_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QARepositoryItem, Member, Profile)
        .outerjoin(Member, QARepositoryItem.created_by == Member.id)
        .outerjoin(Profile, Member.profile_id == Profile.id)
        .where(QARepositoryItem.trial_id == trial_id)
        .order_by(QARepositoryItem.created_at.desc())
    )
    rows = result.all()
    return [
        QAItemResponse(
            id=qa.id,
            trial_id=qa.trial_id,
            question=qa.question,
            answer=qa.answer,
            created_by=qa.created_by,
            created_at=qa.created_at,
            updated_at=qa.updated_at,
            tags=qa.tags,
            is_verified=qa.is_verified,
            source=qa.source,
            sources=qa.sources,
            creator_name=m.name if m else None,
            creator_email=m.email if m else None,
        )
        for qa, m, p in rows
    ]


@router.post("/", response_model=QAItemResponse, status_code=201)
async def create_qa_item(
    payload: QAItemCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(QARepositoryItem, db)
    data = payload.model_dump()
    data["created_by"] = member.id
    item = await crud.create(data)
    return QAItemResponse(
        id=item.id,
        trial_id=item.trial_id,
        question=item.question,
        answer=item.answer,
        created_by=item.created_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
        tags=item.tags,
        is_verified=item.is_verified,
        source=item.source,
        sources=item.sources,
        creator_name=member.name,
        creator_email=member.email,
    )


@router.put("/{item_id}/verify", response_model=QAItemResponse)
async def verify_qa_item(
    item_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(QARepositoryItem, db)
    item = await crud.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="QA item not found")
    updated = await crud.update(item_id, {"is_verified": True})
    return updated


@router.delete("/{item_id}", status_code=204)
async def delete_qa_item(
    item_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(QARepositoryItem, db)
    item = await crud.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="QA item not found")
    await crud.delete(item_id)
