"""
Contracts (Pydantic schemas) for the Collaboration Hub API.
Covers: Inbox, Direct Messages, Threads.
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel

# ─────────────────────────────────────────────
# INBOX
# ─────────────────────────────────────────────


class InboxMessageCreate(BaseModel):
    trial_id: Optional[UUID] = None
    sender_name: str
    sender_email: Optional[str] = None
    to_addresses: List[str] = []
    cc_addresses: List[str] = []
    subject: str
    body: str
    labels: List[str] = []
    folder: str = "inbox"
    related_thread_id: Optional[UUID] = None


class InboxMessageUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    folder: Optional[str] = None
    labels: Optional[List[str]] = None
    related_thread_id: Optional[UUID] = None


class InboxReplyCreate(BaseModel):
    to_addresses: List[str]
    cc_addresses: List[str] = []
    body: str


# ─────────────────────────────────────────────
# DIRECT MESSAGES
# ─────────────────────────────────────────────


class DirectMessageCreate(BaseModel):
    recipient_id: UUID
    content: str
    trial_id: Optional[UUID] = None
    task_id: Optional[UUID] = None


# ─────────────────────────────────────────────
# COLLABORATION THREADS
# ─────────────────────────────────────────────


class ThreadAnchor(BaseModel):
    type: str
    id: Optional[str] = None
    label: str


class CollaborationThreadCreate(BaseModel):
    trial_id: Optional[UUID] = None
    title: str
    thread_type: str = "general"
    anchors: List[ThreadAnchor] = []


class CollaborationThreadUpdate(BaseModel):
    title: Optional[str] = None
    thread_type: Optional[str] = None
    anchors: Optional[List[ThreadAnchor]] = None
    is_resolved: Optional[bool] = None
    resolution_summary: Optional[str] = None
    ai_draft_summary: Optional[str] = None


class ThreadMessageCreate(BaseModel):
    content: str
    role: str = "user"
