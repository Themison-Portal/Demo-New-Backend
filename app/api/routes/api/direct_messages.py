"""
Direct message routes.
GET  /conversations              — list all DM conversations for sidebar
GET  /conversations/{partner_id} — messages in a 1:1 conversation
POST /                           — send a new direct message
PUT  /{id}/read                  — mark as read
DELETE /{id}                     — soft delete
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.direct_messages import DirectMessage
from app.models.profiles import Profile
from app.models.tasks import Task
from app.contracts.collaboration import DirectMessageCreate

router = APIRouter()


def _task_card(task: Optional[Task]) -> Optional[Dict]:
    if not task:
        return None
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status if hasattr(task, "status") else None,
        "due_date": (
            task.due_date.isoformat()
            if hasattr(task, "due_date") and task.due_date
            else None
        ),
        "assigned_to": (
            str(task.assigned_to)
            if hasattr(task, "assigned_to") and task.assigned_to
            else None
        ),
    }


def _serialize(dm: DirectMessage, sender=None, recipient=None, task=None) -> Dict:
    return {
        "id": str(dm.id),
        "sender_id": str(dm.sender_id),
        "recipient_id": str(dm.recipient_id),
        "sender_name": (
            f"{sender.first_name} {sender.last_name}".strip() if sender else None
        ),
        "recipient_name": (
            f"{recipient.first_name} {recipient.last_name}".strip()
            if recipient
            else None
        ),
        "content": dm.content,
        "task_id": str(dm.task_id) if dm.task_id else None,
        "task_data": _task_card(task),
        "is_read": dm.is_read,
        "sent_at": dm.sent_at.isoformat() if dm.sent_at else None,
    }


@router.get("/conversations", response_model=List[Dict])
async def list_conversations(
    trial_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    me = member.profile_id

    stmt = select(DirectMessage).where(
        or_(
            DirectMessage.sender_id == me,
            DirectMessage.recipient_id == me,
        ),
        DirectMessage.deleted_at.is_(None),
    )
    if trial_id:
        stmt = stmt.where(DirectMessage.trial_id == trial_id)
    stmt = stmt.order_by(DirectMessage.sent_at.desc())

    result = await db.execute(stmt)
    all_dms = result.scalars().all()

    conversations: Dict[str, Dict] = {}
    for dm in all_dms:
        partner_id = (
            str(dm.recipient_id) if str(dm.sender_id) == str(me) else str(dm.sender_id)
        )
        if partner_id not in conversations:
            conversations[partner_id] = {
                "partner_id": partner_id,
                "last_message": dm.content[:80],
                "last_message_at": dm.sent_at.isoformat() if dm.sent_at else None,
                "unread_count": 0,
            }
        if str(dm.recipient_id) == str(me) and not dm.is_read:
            conversations[partner_id]["unread_count"] += 1

    partner_ids = [UUID(pid) for pid in conversations.keys()]
    if partner_ids:
        profiles_result = await db.execute(
            select(Profile).where(Profile.id.in_(partner_ids))
        )
        profiles = {str(p.id): p for p in profiles_result.scalars().all()}
        for pid, conv in conversations.items():
            p = profiles.get(pid)
            conv["partner_name"] = f"{p.first_name} {p.last_name}".strip() if p else pid
            conv["partner_avatar_url"] = getattr(p, "avatar_url", None) if p else None
            conv["is_online"] = False

    return list(conversations.values())


@router.get("/conversations/{partner_id}", response_model=List[Dict])
async def get_conversation(
    partner_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    me = member.profile_id
    stmt = (
        select(DirectMessage)
        .where(
            or_(
                and_(
                    DirectMessage.sender_id == me,
                    DirectMessage.recipient_id == partner_id,
                ),
                and_(
                    DirectMessage.sender_id == partner_id,
                    DirectMessage.recipient_id == me,
                ),
            ),
            DirectMessage.deleted_at.is_(None),
        )
        .order_by(DirectMessage.sent_at.asc())
    )

    result = await db.execute(stmt)
    dms = result.scalars().all()

    profile_ids = {str(dm.sender_id) for dm in dms} | {
        str(dm.recipient_id) for dm in dms
    }
    profiles = {}
    if profile_ids:
        pr = await db.execute(
            select(Profile).where(Profile.id.in_([UUID(x) for x in profile_ids]))
        )
        profiles = {str(p.id): p for p in pr.scalars().all()}

    task_ids = [dm.task_id for dm in dms if dm.task_id]
    tasks = {}
    if task_ids:
        tr = await db.execute(select(Task).where(Task.id.in_(task_ids)))
        tasks = {str(t.id): t for t in tr.scalars().all()}

    for dm in dms:
        if str(dm.recipient_id) == str(me) and not dm.is_read:
            dm.is_read = True
            db.add(dm)
    await db.commit()

    return [
        _serialize(
            dm,
            sender=profiles.get(str(dm.sender_id)),
            recipient=profiles.get(str(dm.recipient_id)),
            task=tasks.get(str(dm.task_id)) if dm.task_id else None,
        )
        for dm in dms
    ]


@router.post("/", status_code=201)
async def send_direct_message(
    payload: DirectMessageCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    dm = DirectMessage(
        organization_id=member.organization_id,
        trial_id=payload.trial_id,
        sender_id=member.profile_id,
        recipient_id=payload.recipient_id,
        content=payload.content,
        task_id=payload.task_id,
        sent_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(dm)
    await db.commit()
    await db.refresh(dm)

    sender = (
        (await db.execute(select(Profile).where(Profile.id == dm.sender_id)))
        .scalars()
        .first()
    )
    recipient = (
        (await db.execute(select(Profile).where(Profile.id == dm.recipient_id)))
        .scalars()
        .first()
    )
    task = None
    if dm.task_id:
        task = (
            (await db.execute(select(Task).where(Task.id == dm.task_id)))
            .scalars()
            .first()
        )

    return _serialize(dm, sender=sender, recipient=recipient, task=task)


@router.put("/{message_id}/read", status_code=200)
async def mark_as_read(
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    dm = (
        (
            await db.execute(
                select(DirectMessage).where(
                    DirectMessage.id == message_id,
                    DirectMessage.recipient_id == member.profile_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not dm:
        raise HTTPException(status_code=404, detail="Message not found")
    dm.is_read = True
    dm.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(dm)
    await db.commit()
    return {"success": True}


@router.delete("/{message_id}", status_code=204)
async def delete_direct_message(
    message_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    dm = (
        (
            await db.execute(
                select(DirectMessage).where(
                    DirectMessage.id == message_id,
                    or_(
                        DirectMessage.sender_id == member.profile_id,
                        DirectMessage.recipient_id == member.profile_id,
                    ),
                )
            )
        )
        .scalars()
        .first()
    )
    if not dm:
        raise HTTPException(status_code=404, detail="Message not found")
    dm.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(dm)
    await db.commit()
