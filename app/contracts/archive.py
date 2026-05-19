from datetime import datetime
from typing import Optional
from typing import Any
from uuid import UUID
from pydantic import BaseModel


# ---------------------
# Archive Folder
# ---------------------
class ArchiveFolderCreate(BaseModel):
    org_id: str
    trial_id: Optional[UUID]
    name: str


class ArchiveFolderResponse(BaseModel):
    id: UUID
    user_id: UUID
    org_id: str
    trial_id: Optional[UUID]
    name: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        orm_mode = True


# ---------------------
# Saved Response
# ---------------------
class SavedResponseCreate(BaseModel):
    folder_id: UUID
    org_id: str
    trial_id: Optional[UUID]
    document_id: Optional[UUID]
    title: str
    question: Optional[str]
    answer: Optional[str]
    raw_data: Optional[Any] = None


class SavedResponseUpdate(BaseModel):
    title: Optional[str]
    question: Optional[str]
    answer: Optional[str]
    raw_data: Optional[Any] = None


class SavedResponseResponse(BaseModel):
    id: UUID
    folder_id: UUID
    user_id: UUID
    org_id: str
    trial_id: Optional[UUID]
    document_id: Optional[UUID]
    title: str
    question: Optional[str]
    answer: Optional[str]
    raw_data: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        orm_mode = True
