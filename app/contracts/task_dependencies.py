# app/contracts/task_dependencies.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TaskDependencyResponse(BaseModel):
    id: UUID
    source_task_id: UUID
    target_task_id: UUID
    dependency_type: str
    condition_label: Optional[str] = None
    is_cross_phase: bool = False

    class Config:
        from_attributes = True


class TaskDependencyCreate(BaseModel):
    source_task_id: UUID
    target_task_id: UUID
    dependency_type: Optional[str] = "finish_to_start"
    condition_label: Optional[str] = None
    is_cross_phase: Optional[bool] = False

    class Config:
        from_attributes = True
