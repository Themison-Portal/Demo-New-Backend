"""
Chat session routes — GET /, POST /, PUT /{id}, DELETE /{id}
"""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.chat import ChatSessionCreate, ChatSessionResponse, ChatSessionUpdate
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.chat_sessions import ChatSession
from app.models.members import Member
from app.services.crud import CRUDBase

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_chat_sessions(
    trial_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChatSession).where(
        ChatSession.user_id == member.profile_id
    )
    if trial_id:
        stmt = stmt.where(ChatSession.trial_id == trial_id)
    stmt = stmt.order_by(ChatSession.updated_at.desc())

    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "trial_id": str(s.trial_id) if s.trial_id else None,
            "document_id": str(s.document_id) if s.document_id else None,
            "document_name": s.document_name,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@router.post("/", status_code=201)
async def create_chat_session(
    payload: ChatSessionCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(
        title=payload.title,
        user_id=member.profile_id,
        trial_id=payload.trial_id,
        document_id=payload.document_id,
        document_name=payload.document_name,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "id": str(session.id),
        "title": session.title,
        "trial_id": str(session.trial_id) if session.trial_id else None,
        "document_id": str(session.document_id) if session.document_id else None,
        "document_name": session.document_name,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/{session_id}")
async def get_chat_session(
    session_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == member.profile_id,
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {
        "id": str(session.id),
        "title": session.title,
        "trial_id": str(session.trial_id) if session.trial_id else None,
        "document_id": str(session.document_id) if session.document_id else None,
        "document_name": session.document_name,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.put("/{session_id}")
async def update_chat_session(
    session_id: UUID,
    payload: ChatSessionUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(ChatSession, db)
    session = await crud.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    updated = await crud.update(session_id, payload.model_dump(exclude_unset=True))
    return {"id": str(updated.id), "title": updated.title}


@router.delete("/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    crud = CRUDBase(ChatSession, db)
    session = await crud.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await crud.delete(session_id)
