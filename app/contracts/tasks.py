from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AssignedUser(BaseModel):
    id: UUID
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class TaskResponse(BaseModel):
    id: UUID
    trial_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    due_date: Optional[date] = None
    assigned_to: Optional[UUID] = None
    assigned_user: Optional[AssignedUser] = None
    patient_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    activity_type_id: Optional[UUID] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TaskCreate(BaseModel):
    trial_id: UUID
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo"
    priority: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    patient_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    activity_type_id: Optional[UUID] = None
    category: Optional[str] = None

    class Config:
        orm_mode = True


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    patient_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    activity_type_id: Optional[UUID] = None
    category: Optional[str] = None

    class Config:
        orm_mode = True
