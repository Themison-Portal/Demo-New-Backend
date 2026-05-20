"""
Collaboration thread routes.
GET  /                           — list threads
POST /                           — create thread
GET  /{id}                       — get thread + messages
PUT  /{id}                       — update thread
DELETE /{id}                     — soft delete
POST /{id}/resolve               — mark resolved
POST /{id}/messages              — post a reply
DELETE /{id}/messages/{msg_id}   — soft-delete a reply
POST /{id}/ai-draft              — trigger Themison AI to draft a summary
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile
from app.models.collaboration_threads import (
    CollaborationThread,
    CollaborationThreadMessage,
)
from app.contracts.collaboration import (
    CollaborationThreadCreate,
    CollaborationThreadUpdate,
    ThreadMessageCreate,
)

router = APIRouter()


def _serialize_message(m: CollaborationThreadMessage, sender=None) -> Dict:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "sender_id": str(m.sender_id) if m.sender_id else None,
        "sender_name": (
            f"{sender.first_name} {sender.last_name}".strip()
            if sender
            else ("Themison AI" if m.role == "ai" else None)
        ),
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _serialize_thread(
    thread: CollaborationThread, db: AsyncSession, include_messages: bool = False
) -> Dict:
    reply_count = (
        await db.execute(
            select(func.count()).where(
                CollaborationThreadMessage.thread_id == thread.id,
                CollaborationThreadMessage.deleted_at.is_(None),
            )
        )
    ).scalar() or 0

    sender_rows = (
        (
            await db.execute(
                select(CollaborationThreadMessage.sender_id)
                .where(
                    CollaborationThreadMessage.thread_id == thread.id,
                    CollaborationThreadMessage.sender_id.isnot(None),
                    CollaborationThreadMessage.deleted_at.is_(None),
                )
                .distinct()
                .limit(3)
            )
        )
        .scalars()
        .all()
    )

    avatars: List[Optional[str]] = []
    if sender_rows:
        profiles = (
            (await db.execute(select(Profile).where(Profile.id.in_(sender_rows))))
            .scalars()
            .all()
        )
        avatars = [getattr(p, "avatar_url", None) for p in profiles]

    messages_data = None
    if include_messages:
        msgs = (
            (
                await db.execute(
                    select(CollaborationThreadMessage)
                    .where(
                        CollaborationThreadMessage.thread_id == thread.id,
                        CollaborationThreadMessage.deleted_at.is_(None),
                    )
                    .order_by(CollaborationThreadMessage.created_at.asc())
                )
            )
            .scalars()
            .all()
        )

        sender_ids = [m.sender_id for m in msgs if m.sender_id]
        profiles_map = {}
        if sender_ids:
            pr = (
                (await db.execute(select(Profile).where(Profile.id.in_(sender_ids))))
                .scalars()
                .all()
            )
            profiles_map = {str(p.id): p for p in pr}

        messages_data = [
            _serialize_message(m, profiles_map.get(str(m.sender_id))) for m in msgs
        ]

    return {
        "id": str(thread.id),
        "trial_id": str(thread.trial_id) if thread.trial_id else None,
        "title": thread.title,
        "thread_type": thread.thread_type,
        "anchors": thread.anchors or [],
        "is_resolved": thread.is_resolved,
        "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
        "resolution_summary": thread.resolution_summary,
        "ai_draft_summary": thread.ai_draft_summary,
        "created_by": str(thread.created_by) if thread.created_by else None,
        "reply_count": reply_count,
        "participant_avatars": avatars,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
        "messages": messages_data,
    }


@router.get("/", response_model=List[Dict])
async def list_threads(
    trial_id: Optional[UUID] = None,
    thread_type: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    search: Optional[str] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CollaborationThread).where(
        CollaborationThread.organization_id == member.organization_id,
        CollaborationThread.deleted_at.is_(None),
    )
    if trial_id:
        stmt = stmt.where(CollaborationThread.trial_id == trial_id)
    if thread_type:
        stmt = stmt.where(CollaborationThread.thread_type == thread_type)
    if is_resolved is not None:
        stmt = stmt.where(CollaborationThread.is_resolved == is_resolved)
    if search:
        stmt = stmt.where(CollaborationThread.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(CollaborationThread.updated_at.desc())
    result = await db.execute(stmt)
    threads = result.scalars().all()
    return [await _serialize_thread(t, db) for t in threads]


@router.post("/", status_code=201)
async def create_thread(
    payload: CollaborationThreadCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = CollaborationThread(
        organization_id=member.organization_id,
        trial_id=payload.trial_id,
        title=payload.title,
        thread_type=payload.thread_type,
        anchors=[a.model_dump() for a in payload.anchors],
        created_by=member.profile_id,
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return await _serialize_thread(thread, db)


@router.get("/{thread_id}")
async def get_thread(
    thread_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                    CollaborationThread.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return await _serialize_thread(thread, db, include_messages=True)


@router.put("/{thread_id}")
async def update_thread(
    thread_id: UUID,
    payload: CollaborationThreadUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                    CollaborationThread.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    data = payload.model_dump(exclude_unset=True)
    if "anchors" in data and data["anchors"] is not None:
        data["anchors"] = [
            a if isinstance(a, dict) else a.model_dump() for a in payload.anchors
        ]

    for field, value in data.items():
        setattr(thread, field, value)

    thread.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return await _serialize_thread(thread, db)


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if thread.created_by != member.profile_id and member.default_role not in [
        "admin",
        "staff",
    ]:
        raise HTTPException(status_code=403, detail="Not authorized")

    thread.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(thread)
    await db.commit()


@router.post("/{thread_id}/resolve")
async def resolve_thread(
    thread_id: UUID,
    resolution_summary: Optional[str] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                    CollaborationThread.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.is_resolved = True
    thread.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    thread.resolved_by = member.profile_id
    if resolution_summary:
        thread.resolution_summary = resolution_summary
    thread.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return await _serialize_thread(thread, db)


@router.post("/{thread_id}/messages", status_code=201)
async def post_thread_message(
    thread_id: UUID,
    payload: ThreadMessageCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                    CollaborationThread.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    msg = CollaborationThreadMessage(
        thread_id=thread_id,
        sender_id=member.profile_id if payload.role == "user" else None,
        role=payload.role,
        content=payload.content,
    )
    db.add(msg)
    thread.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(thread)
    await db.commit()
    await db.refresh(msg)

    sender = None
    if msg.sender_id:
        sender = (
            (await db.execute(select(Profile).where(Profile.id == msg.sender_id)))
            .scalars()
            .first()
        )

    return _serialize_message(msg, sender)


@router.delete("/{thread_id}/messages/{message_id}", status_code=204)
async def delete_thread_message(
    thread_id: UUID,
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = (
        (
            await db.execute(
                select(CollaborationThreadMessage).where(
                    CollaborationThreadMessage.id == message_id,
                    CollaborationThreadMessage.thread_id == thread_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if str(msg.sender_id) != str(member.profile_id) and member.default_role not in [
        "admin",
        "staff",
    ]:
        raise HTTPException(status_code=403, detail="Not authorized")

    msg.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(msg)
    await db.commit()


@router.post("/{thread_id}/ai-draft")
async def ai_draft_summary(
    thread_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    thread = (
        (
            await db.execute(
                select(CollaborationThread).where(
                    CollaborationThread.id == thread_id,
                    CollaborationThread.organization_id == member.organization_id,
                    CollaborationThread.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.ai_draft_summary = (
        f"AI summary for '{thread.title}' — replace with LLM output."
    )
    thread.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)

    return {"ai_draft_summary": thread.ai_draft_summary}
