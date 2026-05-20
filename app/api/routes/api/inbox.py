"""
Inbox routes — GET /  POST /  GET /{id}  PUT /{id}  DELETE /{id}
POST /{id}/reply  POST /{id}/ai-triage
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.inbox_messages import InboxMessage
from app.contracts.collaboration import (
    InboxMessageCreate,
    InboxMessageUpdate,
    InboxReplyCreate,
)

router = APIRouter()


def _serialize(m: InboxMessage) -> Dict:
    return {
        "id": str(m.id),
        "trial_id": str(m.trial_id) if m.trial_id else None,
        "sender_name": m.sender_name,
        "sender_email": m.sender_email,
        "to_addresses": m.to_addresses or [],
        "cc_addresses": m.cc_addresses or [],
        "subject": m.subject,
        "body": m.body,
        "ai_summary": m.ai_summary,
        "labels": m.labels or [],
        "folder": m.folder,
        "is_read": m.is_read,
        "is_starred": m.is_starred,
        "related_thread_id": str(m.related_thread_id) if m.related_thread_id else None,
        "received_at": m.received_at.isoformat() if m.received_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/", response_model=List[Dict])
async def list_inbox_messages(
    trial_id: Optional[UUID] = None,
    folder: str = Query("inbox", description="inbox | sent | draft | archive | unread"),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InboxMessage).where(
        InboxMessage.owner_id == member.profile_id,
        InboxMessage.deleted_at.is_(None),
    )
    if trial_id:
        stmt = stmt.where(InboxMessage.trial_id == trial_id)
    if folder == "unread":
        stmt = stmt.where(InboxMessage.is_read == False)
    else:
        stmt = stmt.where(InboxMessage.folder == folder)

    stmt = stmt.order_by(InboxMessage.received_at.desc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [_serialize(m) for m in messages]


@router.get("/counts", response_model=Dict)
async def inbox_counts(
    trial_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    base = and_(
        InboxMessage.owner_id == member.profile_id,
        InboxMessage.deleted_at.is_(None),
    )
    if trial_id:
        base = and_(base, InboxMessage.trial_id == trial_id)

    total = (
        await db.execute(
            select(func.count()).where(base, InboxMessage.folder == "inbox")
        )
    ).scalar()

    unread = (
        await db.execute(
            select(func.count()).where(
                base, InboxMessage.folder == "inbox", InboxMessage.is_read == False
            )
        )
    ).scalar()

    sent = (
        await db.execute(
            select(func.count()).where(base, InboxMessage.folder == "sent")
        )
    ).scalar()

    draft = (
        await db.execute(
            select(func.count()).where(base, InboxMessage.folder == "draft")
        )
    ).scalar()

    return {
        "inbox": total,
        "unread": unread,
        "sent": sent,
        "draft": draft,
    }


@router.post("/", status_code=201)
async def create_inbox_message(
    payload: InboxMessageCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = InboxMessage(
        organization_id=member.organization_id,
        trial_id=payload.trial_id,
        owner_id=member.profile_id,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        to_addresses=payload.to_addresses,
        cc_addresses=payload.cc_addresses,
        subject=payload.subject,
        body=payload.body,
        labels=payload.labels,
        folder=payload.folder,
        related_thread_id=payload.related_thread_id,
        received_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return _serialize(msg)


@router.get("/{message_id}")
async def get_inbox_message(
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = (
        (
            await db.execute(
                select(InboxMessage).where(
                    InboxMessage.id == message_id,
                    InboxMessage.owner_id == member.profile_id,
                    InboxMessage.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Inbox message not found")

    if not msg.is_read:
        msg.is_read = True
        msg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

    return _serialize(msg)


@router.put("/{message_id}")
async def update_inbox_message(
    message_id: UUID,
    payload: InboxMessageUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = (
        (
            await db.execute(
                select(InboxMessage).where(
                    InboxMessage.id == message_id,
                    InboxMessage.owner_id == member.profile_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Inbox message not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(msg, field, value)
    msg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return _serialize(msg)


@router.delete("/{message_id}", status_code=204)
async def delete_inbox_message(
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = (
        (
            await db.execute(
                select(InboxMessage).where(
                    InboxMessage.id == message_id,
                    InboxMessage.owner_id == member.profile_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Inbox message not found")

    msg.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(msg)
    await db.commit()


@router.post("/{message_id}/reply", status_code=201)
async def reply_to_inbox_message(
    message_id: UUID,
    payload: InboxReplyCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    original = (
        (
            await db.execute(
                select(InboxMessage).where(
                    InboxMessage.id == message_id,
                    InboxMessage.owner_id == member.profile_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not original:
        raise HTTPException(status_code=404, detail="Inbox message not found")

    reply = InboxMessage(
        organization_id=member.organization_id,
        trial_id=original.trial_id,
        owner_id=member.profile_id,
        sender_name=str(member.profile_id),
        sender_email=None,
        to_addresses=payload.to_addresses,
        cc_addresses=payload.cc_addresses,
        subject=f"Re: {original.subject}",
        body=payload.body,
        labels=[],
        folder="sent",
        related_thread_id=original.related_thread_id,
        received_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return _serialize(reply)


@router.post("/{message_id}/ai-triage", status_code=200)
async def ai_triage_message(
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    msg = (
        (
            await db.execute(
                select(InboxMessage).where(
                    InboxMessage.id == message_id,
                    InboxMessage.owner_id == member.profile_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Inbox message not found")

    if not msg.ai_summary:
        msg.ai_summary = f"{msg.subject} — awaiting AI triage."
        msg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

    return {"ai_summary": msg.ai_summary, "labels": msg.labels}
