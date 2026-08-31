"""
Suggestion feedback routes — good/needs-work ratings on AI responses
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.suggestion_feedback import (
    SuggestionFeedbackCreate,
    SuggestionFeedbackResponse,
)
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.suggestion_feedback import SuggestionFeedback, FeedbackStatus
from app.models.members import Member

router = APIRouter()


@router.post("/feedback/", response_model=SuggestionFeedbackResponse, status_code=201)
async def create_suggestion_feedback(
    payload: SuggestionFeedbackCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    feedback = SuggestionFeedback(
        org_id=payload.org_id,
        user_id=member.id,
        trial_id=payload.trial_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        question=payload.question,
        answer=payload.answer,
        label=payload.label,
        status=payload.status,
        comment=payload.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.get("/feedback/", response_model=List[SuggestionFeedbackResponse])
async def list_suggestion_feedback(
    org_id: str,
    status: Optional[FeedbackStatus] = None,
    trial_id: Optional[str] = None,  # pass a UUID string, or "null" for the "No trial" group
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    query = select(SuggestionFeedback).where(SuggestionFeedback.org_id == org_id)
    if status:
        query = query.where(SuggestionFeedback.status == status)
    if trial_id == "null":
        query = query.where(SuggestionFeedback.trial_id.is_(None))
    elif trial_id:
        query = query.where(SuggestionFeedback.trial_id == UUID(trial_id))
    query = query.order_by(SuggestionFeedback.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/feedback/{feedback_id}", status_code=204)
async def delete_suggestion_feedback(
    feedback_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    feedback = (
        (await db.execute(select(SuggestionFeedback).where(SuggestionFeedback.id == feedback_id)))
        .scalars()
        .first()
    )
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    await db.delete(feedback)
    await db.commit()