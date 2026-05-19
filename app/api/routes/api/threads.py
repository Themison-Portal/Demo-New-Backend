# from datetime import datetime, timezone
# from typing import Dict, List, Optional
# from uuid import UUID

# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy import select, desc
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.dependencies.auth import get_current_member
# from app.dependencies.db import get_db

# # from app.models.chat_threads import ChatThread
# from app.models.chat_messages import ChatMessage
# from app.models.thread_participants import ThreadParticipant
# from app.models.members import Member
# from app.contracts.thread_chat import ThreadCreate, ThreadUpdate

# router = APIRouter()


# # -------------------------------
# # List threads
# # -------------------------------
# @router.get("/", response_model=List[Dict])
# async def list_threads(
#     trial_id: Optional[UUID] = None,
#     member: Member = Depends(get_current_member),
#     db: AsyncSession = Depends(get_db),
# ):
#     stmt = (
#         select(ChatThread)
#         .where(ThreadParticipant.user_id == member.profile_id)
#         .join(ThreadParticipant, ThreadParticipant.thread_id == ChatThread.id)
#     )

#     if trial_id:
#         stmt = stmt.where(ChatThread.trial_id == trial_id)

#     stmt = stmt.order_by(ChatThread.updated_at.desc())
#     result = await db.execute(stmt)
#     threads = result.scalars().all()

#     return [
#         {
#             "id": str(t.id),
#             "title": t.title,
#             "trial_id": str(t.trial_id) if t.trial_id else None,
#             "created_at": t.created_at.isoformat() if t.created_at else None,
#             "updated_at": t.updated_at.isoformat() if t.updated_at else None,
#         }
#         for t in threads
#     ]


# # -------------------------------
# # Create thread
# # -------------------------------
# @router.post("/", status_code=201)
# async def create_thread(
#     payload: ThreadCreate,
#     member: Member = Depends(get_current_member),
#     db: AsyncSession = Depends(get_db),
# ):
#     thread = ChatThread(
#         title=payload.title,
#         trial_id=payload.trial_id,
#         created_by=member.profile_id,
#     )
#     db.add(thread)
#     await db.commit()
#     await db.refresh(thread)

#     # Add creator as participant
#     participant = ThreadParticipant(
#         thread_id=thread.id,
#         user_id=member.profile_id,
#         last_read_message_id=None,
#     )
#     db.add(participant)
#     await db.commit()

#     return {
#         "id": str(thread.id),
#         "title": thread.title,
#         "trial_id": str(thread.trial_id) if thread.trial_id else None,
#         "created_at": thread.created_at.isoformat() if thread.created_at else None,
#     }


# # -------------------------------
# # Update thread
# # -------------------------------
# @router.put("/{thread_id}")
# async def update_thread(
#     thread_id: UUID,
#     payload: ThreadUpdate,
#     member: Member = Depends(get_current_member),
#     db: AsyncSession = Depends(get_db),
# ):
#     stmt = select(ChatThread).where(ChatThread.id == thread_id)
#     result = await db.execute(stmt)
#     thread = result.scalar()
#     if not thread:
#         raise HTTPException(status_code=404, detail="Thread not found")

#     # Optional: Only creator/admin can update
#     if thread.created_by != member.profile_id and member.org_role not in [
#         "superadmin",
#         "admin",
#     ]:
#         raise HTTPException(status_code=403, detail="Not authorized to update thread")

#     for key, value in payload.model_dump(exclude_unset=True).items():
#         setattr(thread, key, value)
#     thread.updated_at = datetime.now(timezone.utc)
#     db.add(thread)
#     await db.commit()
#     await db.refresh(thread)

#     return {"id": str(thread.id), "title": thread.title}


# # -------------------------------
# # Delete thread (soft delete)
# # -------------------------------
# @router.delete("/{thread_id}", status_code=204)
# async def delete_thread(
#     thread_id: UUID,
#     member: Member = Depends(get_current_member),
#     db: AsyncSession = Depends(get_db),
# ):
#     stmt = select(ChatThread).where(ChatThread.id == thread_id)
#     result = await db.execute(stmt)
#     thread = result.scalar()
#     if not thread:
#         raise HTTPException(status_code=404, detail="Thread not found")

#     # Optional: Only creator/admin can delete
#     if thread.created_by != member.profile_id and member.org_role not in [
#         "superadmin",
#         "admin",
#     ]:
#         raise HTTPException(status_code=403, detail="Not authorized to delete thread")

#     thread.deleted_at = datetime.now(timezone.utc)
#     db.add(thread)
#     await db.commit()


# # -------------------------------
# # Mark thread as read
# # -------------------------------
# @router.post("/{thread_id}/read")
# async def mark_thread_as_read(
#     thread_id: UUID,
#     member: Member = Depends(get_current_member),
#     db: AsyncSession = Depends(get_db),
# ):
#     # Get last message
#     stmt = (
#         select(ChatMessage.id)
#         .where(ChatMessage.thread_id == thread_id)
#         .where(ChatMessage.deleted_at.is_(None))
#         .order_by(desc(ChatMessage.sent_at))
#         .limit(1)
#     )
#     result = await db.execute(stmt)
#     last_message_id = result.scalar()
#     if not last_message_id:
#         raise HTTPException(status_code=404, detail="No messages found in thread")

#     # Update participant
#     stmt = (
#         select(ThreadParticipant)
#         .where(ThreadParticipant.thread_id == thread_id)
#         .where(ThreadParticipant.user_id == member.profile_id)
#     )
#     result = await db.execute(stmt)
#     participant = result.scalar()
#     if not participant:
#         raise HTTPException(status_code=404, detail="Participant not found")

#     participant.last_read_message_id = last_message_id
#     await db.commit()

#     return {"success": True}
